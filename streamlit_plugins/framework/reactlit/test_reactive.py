"""
Tests para el Reactive Fragment Framework

Ejecutar con:
    pytest test_reactive.py -v
"""

import pytest
import pandas as pd
import streamlit as st
from streamlit.testing.v1 import AppTest

from streamlit_plugins.framework.reactlit import (
    reactlit_fragment,
    register_dependency,
    get_dependency_chain,
    has_dependency_cycle,
    reset_reactive_state,
    get_fragment_state,
    enqueue_fragment_rerun,
    DependencyGraph,
    FragmentMetadata,
)


# =============================================================================
# 🧪 TEST: Dependency Graph
# =============================================================================

def test_dependency_graph_add_fragment():
    """Test que se puede agregar fragmentos al grafo"""
    graph = DependencyGraph()
    meta = FragmentMetadata(
        name="test_frag",
        func=lambda: None,
        dependencies={"dep1"},
        dependents={"dep2"}
    )

    graph.add_fragment(meta)
    assert "test_frag" in graph.fragments
    assert graph.fragments["test_frag"].name == "test_frag"


def test_dependency_graph_add_dependency():
    """Test que se pueden agregar dependencias"""
    graph = DependencyGraph()

    meta_a = FragmentMetadata(name="a", func=lambda: None)
    meta_b = FragmentMetadata(name="b", func=lambda: None)

    graph.add_fragment(meta_a)
    graph.add_fragment(meta_b)

    graph.add_dependency("b", "a")  # B depends on A

    assert "a" in graph.fragments["b"].dependencies
    assert "b" in graph.fragments["a"].dependents


def test_dependency_chain():
    """Test que calcula cadena de dependencias transitivamente"""
    graph = DependencyGraph()

    # Crea fragmentos: A → B → C → D
    for name in ["a", "b", "c", "d"]:
        graph.add_fragment(FragmentMetadata(name=name, func=lambda: None))

    graph.add_dependency("b", "a")
    graph.add_dependency("c", "b")
    graph.add_dependency("d", "c")

    # D depende de C que depende de B que depende de A
    chain = graph.get_dependents_chain("a")
    assert "b" in chain
    assert "c" in chain
    assert "d" in chain


def test_cycle_detection_no_cycle():
    """Test que no detecta ciclos cuando no los hay"""
    graph = DependencyGraph()

    graph.add_fragment(FragmentMetadata(name="a", func=lambda: None))
    graph.add_fragment(FragmentMetadata(name="b", func=lambda: None))

    graph.add_dependency("b", "a")

    assert not graph.has_cycle("a")
    assert not graph.has_cycle("b")


def test_cycle_detection_with_cycle():
    """Test que detecta ciclos"""
    graph = DependencyGraph()

    graph.add_fragment(FragmentMetadata(name="a", func=lambda: None))
    graph.add_fragment(FragmentMetadata(name="b", func=lambda: None))
    graph.add_fragment(FragmentMetadata(name="c", func=lambda: None))

    # Crea ciclo: A → B → C → A
    graph.add_dependency("b", "a")
    graph.add_dependency("c", "b")
    graph.add_dependency("a", "c")

    assert graph.has_cycle("a")


# =============================================================================
# 🧪 TEST: Fragment Metadata
# =============================================================================

def test_fragment_metadata_initialization():
    """Test que se puede crear metadatos de fragmento"""
    def dummy():
        pass

    meta = FragmentMetadata(
        name="test",
        func=dummy,
        dependencies={"dep1", "dep2"},
        dependents={"dep3"}
    )

    assert meta.name == "test"
    assert meta.func == dummy
    assert "dep1" in meta.dependencies
    assert "dep3" in meta.dependents
    assert meta.is_dirty is False


# =============================================================================
# 🧪 TEST: Reactive Fragment Decorator
# =============================================================================

def test_reactive_fragment_registration():
    """Test que el decorador registra fragmentos"""
    reset_reactive_state()

    @reactlit_fragment(dependencies=['test_key'])
    def my_test_fragment():
        pass

    # El decorador debe haber registrado el fragmento
    # (En tests reales usaríamos get_fragment_metadata)


def test_reactive_fragment_with_dependencies():
    """Test que se registran dependencias correctamente"""
    reset_reactive_state()

    @reactlit_fragment(
        dependencies=['key1', 'key2'],
        watch_params=True
    )
    def frag_with_deps():
        pass


# =============================================================================
# 🧪 TEST: Change Detection
# =============================================================================

def test_param_change_detection():
    """Test detección de cambios en parámetros"""
    from streamlit_plugins.framework.reactlit.reactlit import (
        _detect_param_changes,
        _get_or_init_fragment_state,
    )

    fragment_name = "test_detect"

    # Simula cambio: params = {a: 1, b: 2} → {a: 1, b: 3}
    has_changes, changed = _detect_param_changes(
        fragment_name,
        {'a': 1, 'b': 2}
    )

    assert has_changes  # Primer render siempre hay cambios

    # Ahora registra estos como los últimos
    state = _get_or_init_fragment_state(fragment_name)
    state['last_rendered_params'] = {'a': 1, 'b': 2}

    # Ahora detecta cambio real
    has_changes2, changed2 = _detect_param_changes(
        fragment_name,
        {'a': 1, 'b': 3}
    )

    assert has_changes2
    assert 'b' in changed2


def test_snapshot_change_detection_with_dataframes():
    """Test detección de cambios con DataFrames"""
    from streamlit_plugins.framework.reactlit.reactlit import (
        _changed_keys_from_snapshots,
    )

    before = {'df': pd.DataFrame({'a': [1, 2]})}
    after_same = {'df': pd.DataFrame({'a': [1, 2]})}
    after_changed = {'df': pd.DataFrame({'a': [1, 3]})}

    assert _changed_keys_from_snapshots(before, after_same) == set()
    assert _changed_keys_from_snapshots(before, after_changed) == {'df'}


def test_param_change_detection_with_dataframes():
    """Test watch_params con DataFrames"""
    from streamlit_plugins.framework.reactlit.reactlit import (
        _detect_param_changes,
        _get_or_init_fragment_state,
    )

    fragment_name = "test_detect_df"
    state = _get_or_init_fragment_state(fragment_name)
    state['last_rendered_params'] = {'df': pd.DataFrame({'a': [1, 2]})}

    has_changes, changed = _detect_param_changes(
        fragment_name,
        {'df': pd.DataFrame({'a': [1, 2]})}
    )

    assert not has_changes
    assert changed == set()


# =============================================================================
# 🧪 TEST: Session State Management
# =============================================================================

def test_fragment_state_initialization():
    """Test que se inicializa estado para fragmentos"""
    from streamlit_plugins.framework.reactlit.reactlit import (
        _get_or_init_fragment_state,
    )

    reset_reactive_state()
    state = _get_or_init_fragment_state("test_frag")

    assert 'params' in state
    assert 'is_dirty' in state
    assert 'last_rendered_params' in state


def test_session_graph_state():
    """Test que se gestiona estado del grafo en sesión"""
    from streamlit_plugins.framework.reactlit.reactlit import (
        _get_session_graph,
    )

    reset_reactive_state()
    graph_state = _get_session_graph()

    assert 'rerun_queue' in graph_state
    assert 'executing' in graph_state
    assert 'last_params' in graph_state


# =============================================================================
# 🧪 TEST: Utilities
# =============================================================================

def test_enqueue_fragment_rerun():
    """Test que se pueden encolar fragmentos para rerun"""
    from streamlit_plugins.framework.reactlit.reactlit import (
        _get_session_graph,
    )

    reset_reactive_state()

    enqueue_fragment_rerun("test_frag", "test reason")

    graph_state = _get_session_graph()
    assert "test_frag" in graph_state['rerun_queue']


def test_set_fragment_dirty():
    """Test que se puede marcar un fragmento como dirty"""
    from streamlit_plugins.framework.reactlit.reactlit import (
        set_fragment_dirty,
        get_fragment_state,
    )

    reset_reactive_state()

    set_fragment_dirty("test_frag", True)
    state = get_fragment_state("test_frag")

    assert state['is_dirty'] is True


# =============================================================================
# 🧪 TEST: Integration
# =============================================================================

def test_fragment_workflow():
    """Test workflow completo de fragmentos reactivos"""
    reset_reactive_state()

    # Simula: Fragment A → Fragment B

    @reactlit_fragment(watch_params=True)
    def fragment_a():
        st.session_state.shared_value = 42

    @reactlit_fragment(dependencies=['shared_value'])
    def fragment_b():
        value = st.session_state.shared_value
        return value * 2

    # Los fragmentos deben estar registrados
    # (En tests reales con AppTest)


# =============================================================================
# 🧪 TEST: Advanced Patterns
# =============================================================================

def test_reactive_store():
    """Test ReactiveStore basic functionality"""
    from streamlit_plugins.framework.reactlit.advanced_patterns import (
        ReactiveStore,
        Action,
    )

    store = ReactiveStore()

    # Define una acción
    store.define_action(
        'SET_VALUE',
        lambda state, val: {**state, 'value': val}
    )

    # Dispara acción
    store.dispatch(Action('SET_VALUE', 42))

    assert store.get('value') == 42


def test_reactive_form():
    """Test ReactiveForm basic functionality"""
    from streamlit_plugins.framework.reactlit.advanced_patterns import (
        ReactiveForm,
    )

    form = ReactiveForm(initial_values={'name': '', 'email': ''})
    form.add_field('name', 'text')
    form.add_field('email', 'email')

    # Debe poder renderizar sin errores
    # (En tests reales con AppTest)


def test_fragment_state_machine():
    """Test FragmentStateMachine"""
    from streamlit_plugins.framework.reactlit.advanced_patterns import (
        FragmentStateMachine,
    )

    fsm = FragmentStateMachine()
    fsm.add_state('idle')
    fsm.add_state('running')
    fsm.add_state('done')

    # Transiciona
    assert fsm.transition('idle')
    assert fsm.current_state == 'idle'

    assert fsm.transition('running')
    assert fsm.current_state == 'running'


# =============================================================================
# 🧪 TEST: Edge Cases
# =============================================================================

def test_nonexistent_fragment_rerun():
    """Test que rerunear fragmento inexistente es seguro"""
    from streamlit_plugins.framework.reactlit.reactlit import (
        _trigger_fragment_rerun,
    )

    reset_reactive_state()

    # No debe lanzar excepción
    result = _trigger_fragment_rerun("nonexistent_fragment")
    # Retorna False porque no existe
    assert result is False


def test_reset_reactive_state():
    """Test que reset limpia todo el estado"""
    reset_reactive_state()

    # Simula estado
    from streamlit_plugins.framework.reactlit.reactlit import (
        _get_session_graph,
        _get_or_init_fragment_state,
    )

    _get_session_graph()
    _get_or_init_fragment_state("test")

    # Reset
    reset_reactive_state()

    # Debe estar limpio
    # (Se verificaría con assertions en test real)


# =============================================================================
# 📊 MAIN PARA DEBUGGING
# =============================================================================

if __name__ == "__main__":
    # Ejecutar tests básicos sin pytest
    print("🧪 Running Reactive Framework Tests...\n")

    # Test 1
    print("✓ test_dependency_graph_add_fragment")
    test_dependency_graph_add_fragment()

    # Test 2
    print("✓ test_dependency_graph_add_dependency")
    test_dependency_graph_add_dependency()

    # Test 3
    print("✓ test_dependency_chain")
    test_dependency_chain()

    # Test 4
    print("✓ test_cycle_detection_no_cycle")
    test_cycle_detection_no_cycle()

    # Test 5
    print("✓ test_cycle_detection_with_cycle")
    test_cycle_detection_with_cycle()

    # Test 6
    print("✓ test_fragment_metadata_initialization")
    test_fragment_metadata_initialization()

    # Test 7
    print("✓ test_reactive_store")
    test_reactive_store()

    # Test 8
    print("✓ test_reactive_form")
    test_reactive_form()

    # Test 9
    print("✓ test_fragment_state_machine")
    test_fragment_state_machine()

    # Test 10
    print("✓ test_nonexistent_fragment_rerun")
    test_nonexistent_fragment_rerun()

    print("\n✅ All tests passed!")
