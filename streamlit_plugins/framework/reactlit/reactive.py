"""
Reactive Fragment Framework for Streamlit
==========================================

Sistema reactivo para fragmentos en Streamlit que permite:
- Definir fragmentos con dependencias (como componentes React)
- Detectar cambios en dependencias automáticamente
- Ejecutar cascadas de reruns manteniendo el árbol de dependencias (efecto dominó)
- Evitar loops infinitos y manejar ciclos complejos con global rerun seguro
- Mantener estado compartido via session_state
- Controlar delta paths para renderizado en el mismo sitio

Uso:
    @reactive_fragment(
        dependencies=['input_filter', 'user_settings'],
        dependents=['fragment_b', 'fragment_c']
    )
    def my_fragment():
        st.write("Mi componente reactivo")
"""

import functools
import hashlib
import inspect
import traceback
from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Set

import streamlit as st
from streamlit.commands.execution_control import _new_fragment_id_queue
from streamlit.runtime.scriptrunner import get_script_run_ctx, RerunData


# =============================================================================
# 🏗️ CORE DATA STRUCTURES
# =============================================================================

@dataclass
class FragmentMetadata:
    """Metadata para un fragmento reactivo"""
    name: str
    func: Callable
    dependencies: Set[str] = field(default_factory=set)  # Qué state keys observa
    dependents: Set[str] = field(default_factory=set)  # Qué otros fragmentos dependen de este
    param_watchers: dict[str, Any] = field(default_factory=dict)  # {param_name: last_value}
    delta_path: Optional[str] = None
    fragment_id: Optional[str] = None
    is_dirty: bool = False


@dataclass
class DependencyGraph:
    """Grafo de dependencias entre fragmentos"""
    fragments: dict[str, FragmentMetadata] = field(default_factory=dict)

    def add_fragment(self, metadata: FragmentMetadata) -> None:
        self.fragments[metadata.name] = metadata

    def add_dependency(self, fragment: str, depends_on: str) -> None:
        """fragment depende de depends_on"""
        if fragment in self.fragments and depends_on in self.fragments:
            self.fragments[fragment].dependencies.add(depends_on)
            self.fragments[depends_on].dependents.add(fragment)

    def get_dependents_chain(self, fragment_name: str) -> list[str]:
        """
        Retorna todos los fragmentos que dependen transitivamente de este,
        en orden BFS (los directos primero, luego los transitivos).
        """
        visited: Set[str] = set()
        ordered: list[str] = []
        queue: list[str] = [fragment_name]

        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            if current != fragment_name:
                ordered.append(current)
            if current in self.fragments:
                for dep in self.fragments[current].dependents:
                    if dep not in visited:
                        queue.append(dep)

        return ordered

    def has_cycle(self, start: str, current: str = None, visited: Set[str] = None) -> bool:
        """Detecta si existe un ciclo alcanzable desde start"""
        if current is None:
            current = start
            visited = set()

        if current in visited:
            return current == start

        visited.add(current)

        if current in self.fragments:
            for dependent in self.fragments[current].dependents:
                if self.has_cycle(start, dependent, visited.copy()):
                    return True

        return False


# =============================================================================
# 🎛️ GLOBAL STATE MANAGEMENT
# =============================================================================

_GLOBAL_REGISTRY: dict[str, FragmentMetadata] = {}
_GLOBAL_GRAPH: DependencyGraph = DependencyGraph()
_FRAGMENT_ID_TO_NAME: dict[str, str] = {}


def _get_session_graph() -> dict:
    """Obtiene o crea el estado del grafo en session_state"""
    if '_reactive_graph_state' not in st.session_state:
        st.session_state._reactive_graph_state = {
            'rerun_queue': [],       # Lista ordenada de fragmentos pendientes
            'executing': set(),      # Fragmentos ejecutándose ahora mismo
            'last_params': {},
            'fragment_ids': {},
            'global_rerun_count': 0,
            'cycle_detected': False,
            'cycle_fragments': set(),
        }
    return st.session_state._reactive_graph_state


def _get_or_init_fragment_state(fragment_name: str) -> dict:
    """Inicializa estado para un fragmento específico"""
    state_key = f'_fragment_state_{fragment_name}'
    if state_key not in st.session_state:
        st.session_state[state_key] = {
            'params': {},
            'is_dirty': False,
            'last_rendered_params': {},
        }
    return st.session_state[state_key]


def _log(msg: str) -> None:
    st.session_state._reactive_framework_log = (
        st.session_state.get('_reactive_framework_log', []) + [msg]
    )


def _is_fragment_scoped_run(ctx: Any) -> bool:
    """True cuando la ejecución actual fue iniciada por fragment rerun."""
    if ctx is None:
        return False
    fragment_ids_this_run = getattr(ctx, 'fragment_ids_this_run', None)
    return bool(fragment_ids_this_run)


def _all_dependency_keys() -> set[str]:
    """Todas las dependencias declaradas (se usan como keys candidatas de session_state)."""
    keys: set[str] = set()
    for metadata in _GLOBAL_REGISTRY.values():
        keys.update(metadata.dependencies)
    return keys


def _snapshot_session_state(keys: set[str]) -> dict[str, Any]:
    """Snapshot superficial de session_state para las keys observadas."""
    snap: dict[str, Any] = {}
    for key in keys:
        snap[key] = st.session_state.get(key, None)
    return snap


def _changed_keys_from_snapshots(before: dict[str, Any], after: dict[str, Any]) -> set[str]:
    """Detecta qué keys cambiaron entre dos snapshots."""
    changed: set[str] = set()
    all_keys = set(before.keys()) | set(after.keys())
    for key in all_keys:
        if not _values_equal(before.get(key), after.get(key)):
            changed.add(key)
    return changed


def _enqueue_fragments_for_state_changes(current_fragment: str, changed_keys: set[str]) -> None:
    """
    Encola fragmentos que declaran dependencias sobre keys de session_state modificadas.
    """
    if not changed_keys:
        return

    graph_state = _get_session_graph()
    for fragment_name, metadata in _GLOBAL_REGISTRY.items():
        if fragment_name == current_fragment:
            continue
        if not (metadata.dependencies & changed_keys):
            continue

        _get_or_init_fragment_state(fragment_name)['is_dirty'] = True
        if fragment_name not in graph_state['rerun_queue'] and fragment_name not in graph_state['executing']:
            graph_state['rerun_queue'].append(fragment_name)
            _log(f"[ENQUEUE_BY_STATE] {fragment_name} <- keys={sorted(changed_keys)}")


# =============================================================================
# 📍 FRAGMENT TRACKING
# =============================================================================

def _get_fragment_delta_path() -> str:
    """Obtiene el delta path actual del fragmento"""
    ctx = get_script_run_ctx()
    if ctx is None:
        return ""

    # En un fragmento, el delta path es el stack de contenedores donde se define
    dg_stack = getattr(ctx, 'dg', None)
    if dg_stack and hasattr(dg_stack, '_root') and hasattr(dg_stack._root, '_delta_path'):
        return str(dg_stack._root._delta_path)
    return ""


def _get_current_fragment_id() -> Optional[str]:
    """Obtiene el ID del fragmento actual de ejecución"""
    ctx = get_script_run_ctx()
    if ctx is None:
        return None

    # El fragment_id se asigna durante la ejecución del fragmento
    return getattr(ctx, 'current_fragment_id', None)


# =============================================================================
# 🔄 CHANGE DETECTION
# =============================================================================

def _values_equal(left: Any, right: Any) -> bool:
    """Compara valores escalares y array-like sin romper con pandas."""
    if left is right:
        return True

    for candidate, other in ((left, right), (right, left)):
        equals = getattr(candidate, "equals", None)
        if callable(equals):
            try:
                return bool(equals(other))
            except Exception:
                pass

    try:
        result = left == right
    except Exception:
        return False

    while not isinstance(result, bool):
        all_method = getattr(result, "all", None)
        if not callable(all_method):
            break
        try:
            result = all_method()
        except Exception:
            break

    try:
        return bool(result)
    except Exception:
        return False

def _compute_param_hash(params: dict) -> str:
    """Calcula un hash de los parámetros para detectar cambios"""
    try:
        param_str = str(sorted(params.items()))
        return hashlib.md5(param_str.encode()).hexdigest()
    except Exception:
        return "unknown"


def _detect_param_changes(
    fragment_name: str,
    current_params: dict[str, Any],
) -> tuple[bool, Set[str]]:
    """
    Detecta si los parámetros han cambiado respecto al último render.
    Retorna: (hay_cambios, parámetros_que_cambiaron)
    """
    state = _get_or_init_fragment_state(fragment_name)
    last_params = state.get('last_rendered_params', {})

    changed: Set[str] = set()
    for key, new_value in current_params.items():
        if not _values_equal(last_params.get(key), new_value):
            changed.add(key)
    for key in last_params:
        if key not in current_params:
            changed.add(key)

    return len(changed) > 0, changed



def _enqueue_dependents(fragment_name: str, graph: DependencyGraph, reason: str = "") -> None:
    """
    Marca como dirty y encola en rerun_queue todos los dependientes
    de fragment_name, en orden BFS (directos primero).
    """
    graph_state = _get_session_graph()
    dependents = graph.get_dependents_chain(fragment_name)

    for dep in dependents:
        # Marcar como dirty
        _get_or_init_fragment_state(dep)['is_dirty'] = True

        # Encolar solo si no está ya ni ejecutándose
        if dep not in graph_state['rerun_queue'] and dep not in graph_state['executing']:
            graph_state['rerun_queue'].append(dep)
            _log(f"[ENQUEUE] {dep} ← {fragment_name}{' (' + reason + ')' if reason else ''}")


# =============================================================================
# 🔁 CICLOS COMPLEJOS Y GLOBAL RERUN
# =============================================================================
# El flag de global rerun se guarda en una clave separada de session_state
# (_reactive_global_rerun_flag) para que sobreviva al borrado del graph_state.

def _detect_complex_cycles(graph: DependencyGraph) -> tuple[bool, Set[str]]:
    """Detecta fragmentos que forman parte de un ciclo en el grafo."""
    with_cycles: Set[str] = set()
    for name in graph.fragments:
        if graph.has_cycle(name):
            with_cycles.add(name)
    return len(with_cycles) > 0, with_cycles


def _trigger_global_rerun() -> bool:
    """
    Dispara un rerun global (full reset).
    Si ya se disparó uno y se intenta otro, hay un bug → error crítico.
    Retorna True si procede, False si es bug.
    """
    # Usamos clave independiente para que sobreviva al reset del graph_state
    if st.session_state.get('_reactive_global_rerun_flag', False):
        st.error(
            "🚨 **CRITICAL BUG DETECTED**: "
            "Multiple global reruns attempted. "
            "State is inconsistent. Please manually refresh the page."
        )
        _log("[ERROR] Multiple global reruns - state corrupted, execution stopped")
        return False

    st.session_state._reactive_global_rerun_flag = True
    graph_state = _get_session_graph()
    graph_state['global_rerun_count'] += 1
    _log(f"[GLOBAL_RERUN] #{graph_state['global_rerun_count']} - Full reset triggered")
    return True


def _reset_reactive_session_state() -> None:
    """
    Limpia el estado reactivo de fragmentos.
    Preserva _reactive_global_rerun_flag para detectar el caso de bug.
    """
    old_count = 0
    if '_reactive_graph_state' in st.session_state:
        old_count = st.session_state._reactive_graph_state.get('global_rerun_count', 0)
        del st.session_state._reactive_graph_state

    for key in list(st.session_state.keys()):
        if key.startswith('_fragment_state_'):
            del st.session_state[key]

    # Reinicializa preservando el contador
    graph_state = _get_session_graph()
    graph_state['global_rerun_count'] = old_count
    # _reactive_global_rerun_flag NO se borra aquí intencionalmente


# =============================================================================
# 🚀 RERUN MANAGEMENT
# =============================================================================

def _extract_function_from_closure(func: Any) -> Optional[Callable]:
    """Intenta recuperar la función real guardada en freevars del wrapper."""
    closure = getattr(func, '__closure__', None)
    code = getattr(func, '__code__', None)
    if not closure or code is None:
        return None

    freevars = getattr(code, 'co_freevars', ())
    preferred_names = ('non_optional_func', 'func', 'wrapped_func', 'f')

    for name in preferred_names:
        if name in freevars:
            idx = freevars.index(name)
            candidate = closure[idx].cell_contents
            if callable(candidate):
                return candidate

    for cell in closure:
        candidate = getattr(cell, 'cell_contents', None)
        if callable(candidate):
            return candidate

    return None


def _resolve_fragment_callable(wrapper: Any) -> Any:
    """
    Resuelve el callable real detrás del wrapper de Streamlit.
    Prueba unwrap recursivo y fallback a closure.
    """
    current = wrapper

    try:
        unwrapped = inspect.unwrap(current)
        if callable(unwrapped):
            current = unwrapped
    except Exception:
        pass

    for _ in range(8):
        closure_func = _extract_function_from_closure(current)
        if closure_func is None:
            break
        current = closure_func
        try:
            current = inspect.unwrap(current)
        except Exception:
            pass

    return current


def _candidate_fragment_names(wrapper: Any) -> set[str]:
    """Nombres candidatos para hacer matching robusto del fragmento."""
    names: set[str] = set()
    resolved = _resolve_fragment_callable(wrapper)

    for candidate in (wrapper, resolved):
        name = getattr(candidate, '__name__', None)
        if isinstance(name, str) and name:
            names.add(name)
        qualname = getattr(candidate, '__qualname__', None)
        if isinstance(qualname, str) and qualname:
            names.add(qualname.split('.')[-1])

    return names

def _trigger_fragment_rerun(fragment_name: str) -> bool:
    """
    Solicita a Streamlit que rerunnee un fragmento específico por su nombre.
    Retorna True si se encontró y programó, False si no existe.
    """
    ctx = get_script_run_ctx()
    if ctx is None:
        return False

    fragment_storage = getattr(ctx, 'fragment_storage', None)
    if fragment_storage is None:
        return False

    internal_fragments = getattr(fragment_storage, '_fragments', None)
    public_fragments = getattr(fragment_storage, 'fragments', None)
    fragment_map = internal_fragments if internal_fragments is not None else public_fragments
    if fragment_map is None:
        return False

    for fragment_id, fragment_wrapper in fragment_map.items():
        names = _candidate_fragment_names(fragment_wrapper)
        if fragment_name in names:
            _FRAGMENT_ID_TO_NAME[fragment_id] = fragment_name

            # SE SOLICITA EL RERUN
            query_string = ctx.query_string
            page_script_hash = ctx.page_script_hash
            cached_message_hashes = ctx.cached_message_hashes

            # fragment_queue = _new_fragment_id_queue(ctx, "fragment")
            fragment_queue = [fragment_id]
            ctx.script_requests.request_rerun(
                RerunData(
                    query_string=query_string,
                    page_script_hash=page_script_hash,
                    fragment_id_queue=fragment_queue,
                    is_fragment_scoped_rerun=True,
                    cached_message_hashes=cached_message_hashes,
                    context_info=ctx.context_info,
                )
            )
            return True

    return False


def _fire_next_in_queue() -> None:
    """
    Efecto dominó: al terminar un fragmento, dispara el siguiente en la cola.
    Solo dispara si no hay ningún fragmento ejecutándose.
    """
    graph_state = _get_session_graph()

    # Si algo se está ejecutando todavía, no interferir
    if graph_state['executing']:
        return

    queue = graph_state['rerun_queue']
    while queue:
        next_frag = queue.pop(0)

        if next_frag in graph_state['executing']:
            # En ejecución, saltar (no debería pasar pero por seguridad)
            continue

        if next_frag not in _GLOBAL_REGISTRY:
            _log(f"[SKIP] {next_frag} not registered")
            continue

        if _trigger_fragment_rerun(next_frag):
            _log(f"[FIRE] → {next_frag}")
            st.empty()
            break
        else:
            _log(f"[SKIP] {next_frag} not found in fragment storage")


def _queue_fragment_rerun(fragment_name: str, reason: str = "") -> None:
    """Encola manualmente un fragmento para rerun (API pública interna)"""
    graph_state = _get_session_graph()
    if fragment_name not in graph_state['rerun_queue'] and fragment_name not in graph_state['executing']:
        graph_state['rerun_queue'].append(fragment_name)
        _log(f"[QUEUE] {fragment_name}{' (' + reason + ')' if reason else ''}")


# =============================================================================
# 🎨 REACTIVE FRAGMENT DECORATOR
# =============================================================================

def reactive_fragment(
    dependencies: Optional[list[str]] = None,
    dependents: Optional[list[str]] = None,
    watch_params: bool = True,
    prevent_cycles: bool = True,
):
    """
    Decorador para crear fragmentos reactivos.

    Args:
        dependencies: Session state keys o nombres de fragmentos que este observa
        dependents: Fragmentos que dependen de este (se registran como edges en el grafo)
        watch_params: Si True, detecta cambios en parámetros y encola dependientes
        prevent_cycles: Si True, detecta ciclos y dispara global rerun seguro
    """
    dep_list = set(dependencies or [])
    dep_names = set(dependents or [])

    def decorator(func: Callable) -> Callable:
        fragment_name = func.__name__

        metadata = FragmentMetadata(
            name=fragment_name,
            func=func,
            dependencies=dep_list,
            dependents=dep_names,
        )
        _GLOBAL_REGISTRY[fragment_name] = metadata
        _GLOBAL_GRAPH.add_fragment(metadata)

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            ctx = get_script_run_ctx()
            graph_state = _get_session_graph()
            frag_state = _get_or_init_fragment_state(fragment_name)
            fragment_scoped_run = _is_fragment_scoped_run(ctx)

            watched_keys = _all_dependency_keys() if fragment_scoped_run else set()
            before_state = _snapshot_session_state(watched_keys) if watched_keys else {}

            # ── VERIFICACIÓN 1: bug de múltiples global reruns ──────────────
            if st.session_state.get('_reactive_global_rerun_flag', False):
                # Esto se ejecuta cuando el st.rerun() global no detuvo la app
                # antes de que otro fragmento intentara ejecutarse → bug crítico
                st.error(
                    "🚨 **CRITICAL BUG**: Fragment executing after global rerun. "
                    "Please manually refresh the page."
                )
                return None

            # ── VERIFICACIÓN 2: ciclos complejos ────────────────────────────
            if prevent_cycles:
                has_cycles, cycle_frags = _detect_complex_cycles(_GLOBAL_GRAPH)
                if has_cycles and not graph_state['cycle_detected']:
                    graph_state['cycle_detected'] = True
                    graph_state['cycle_fragments'] = cycle_frags
                    _log(f"[CYCLE_DETECTED] {cycle_frags}")

                    if fragment_name in cycle_frags:
                        if _trigger_global_rerun():
                            st.warning(
                                f"🔄 Cycle detected in **{fragment_name}**. "
                                "Performing full reset…"
                            )
                            _reset_reactive_session_state()
                            st.rerun()
                        # Si _trigger_global_rerun devolvió False, ya mostró el error crítico
                        return None

            # ── EJECUCIÓN ────────────────────────────────────────────────────
            # Marcar como en ejecución para evitar disparos duplicados
            graph_state['executing'].add(fragment_name)

            # Actualiza tracking del delta path
            metadata.delta_path = _get_fragment_delta_path()
            metadata.fragment_id = _get_current_fragment_id()

            # Detecta cambios en parámetros de entrada
            sig = inspect.signature(func)
            bound = sig.bind_partial(*args, **kwargs)
            bound.apply_defaults()
            current_params = dict(bound.arguments)

            has_param_changes, changed_params = _detect_param_changes(fragment_name, current_params)

            frag_state['params'] = current_params
            frag_state['last_rendered_params'] = current_params.copy()
            frag_state['is_dirty'] = False

            if has_param_changes and watch_params:
                _log(f"[CHANGE] {fragment_name}: {changed_params}")

            # Ejecuta la función del fragmento
            try:
                result = func(*args, **kwargs)
            except Exception as e:
                st.error(f"Error en fragmento **{fragment_name}**: {e}\n\n{traceback.format_exc()}")
                result = None

            # Termina ejecución
            graph_state['executing'].discard(fragment_name)

            # Solo la ejecución fragment-scoped puede disparar cascadas automáticas
            if fragment_scoped_run:
                after_state = _snapshot_session_state(watched_keys) if watched_keys else {}
                changed_state_keys = _changed_keys_from_snapshots(before_state, after_state)
                if changed_state_keys:
                    _log(f"[STATE_CHANGED] {fragment_name}: {sorted(changed_state_keys)}")
                    _enqueue_fragments_for_state_changes(fragment_name, changed_state_keys)
                    # Mantener también la cascada por arista de fragmentos declaradas
                    _enqueue_dependents(fragment_name, _GLOBAL_GRAPH, reason="state changed")

            # -- EFECTO DOMINÓ: dispara el siguiente fragmento pendiente ──────
            if fragment_scoped_run:
                _fire_next_in_queue()

            return result

        return st.fragment(wrapper)

    return decorator


# =============================================================================
# 🔗 DEPENDENCY REGISTRATION
# =============================================================================

def register_dependency(fragment: str, depends_on: str) -> None:
    """
    Registra que `fragment` depende de `depends_on`.
    Crea un edge en el grafo: depends_on → fragment.
    """
    _GLOBAL_GRAPH.add_dependency(fragment, depends_on)


def register_dependencies(fragment: str, dependencies: list[str]) -> None:
    """Registra múltiples dependencias para un mismo fragmento"""
    for dep in dependencies:
        register_dependency(fragment, dep)


# =============================================================================
# 🔍 QUERY & INTROSPECTION
# =============================================================================

def get_fragment_metadata(fragment_name: str) -> Optional[FragmentMetadata]:
    return _GLOBAL_REGISTRY.get(fragment_name)


def get_all_fragments() -> dict[str, FragmentMetadata]:
    return _GLOBAL_REGISTRY.copy()


def get_dependency_chain(fragment_name: str) -> list[str]:
    """Retorna la cadena BFS de dependientes de un fragmento"""
    return _GLOBAL_GRAPH.get_dependents_chain(fragment_name)


def has_dependency_cycle(fragment_name: str) -> bool:
    return _GLOBAL_GRAPH.has_cycle(fragment_name)


# =============================================================================
# 📊 DEBUGGING & MONITORING
# =============================================================================

def debug_dependency_graph() -> None:
    """Muestra el grafo de dependencias y estado en la UI"""
    with st.expander("🔍 Debug: Reactive Dependency Graph"):
        graph_state = _get_session_graph()

        st.write("**Fragmentos registrados:**")
        for name, meta in _GLOBAL_REGISTRY.items():
            has_cycle = _GLOBAL_GRAPH.has_cycle(name)
            cols = st.columns([2, 2, 2, 1])
            cols[0].write(f"**{name}**")
            cols[1].write(f"deps: {meta.dependencies or '—'}")
            cols[2].write(f"dependents: {meta.dependents or '—'}")
            cols[3].write("⚠️ cycle" if has_cycle else "✅")

        st.write("**Cola de reruns:**", graph_state['rerun_queue'] or "vacía")
        st.write("**Ejecutando:**", graph_state['executing'] or "—")
        st.write("**Global reruns:**", graph_state['global_rerun_count'])
        st.write("**Ciclo detectado:**", graph_state['cycle_detected'])

        st.write("**Logs recientes:**")
        for log in st.session_state.get('_reactive_framework_log', [])[-20:]:
            st.text(log)


def reset_reactive_state() -> None:
    """
    Limpia TODO el estado reactivo incluyendo el flag de global rerun.
    Usar para testing o para reset manual por el usuario.
    """
    for key in list(st.session_state.keys()):
        if key.startswith(('_reactive_', '_fragment_state_')):
            del st.session_state[key]


# =============================================================================
# 🧪 UTILITIES FOR ADVANCED USAGE
# =============================================================================

def get_fragment_state(fragment_name: str) -> dict:
    return _get_or_init_fragment_state(fragment_name).copy()


def set_fragment_dirty(fragment_name: str, dirty: bool = True) -> None:
    _get_or_init_fragment_state(fragment_name)['is_dirty'] = dirty


def enqueue_fragment_rerun(fragment_name: str, reason: str = "") -> None:
    """Encola manualmente un fragmento para rerun y dispara el dominó"""
    _queue_fragment_rerun(fragment_name, reason)
    _fire_next_in_queue()


def manually_trigger_rerun_cascade(root_fragment: str) -> None:
    """Encola todos los dependientes de root_fragment y dispara el dominó"""
    _enqueue_dependents(root_fragment, _GLOBAL_GRAPH, reason="manual cascade")
    _fire_next_in_queue()
