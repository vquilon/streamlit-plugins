import React, { ReactNode } from "react";

import { Streamlit, Theme, withStreamlitConnection, ComponentProps } from "streamlit-component-lib";
import { BaseProvider, LightTheme } from "baseui"

import { Client as Styletron } from "styletron-engine-atomic"
import { Provider as StyletronProvider } from "styletron-react"

// import { createPopper } from '@popperjs/core';
// import { useRenderData } from "./NavBarProvider";

import NavItem from "./NavItem.jsx";
import NavSubItem from "./NavSubItem.jsx";

// Initialize our Styletron engine
const engine = new Styletron()

interface MenuItem {
    icon: string;
    id: string;
    label: string;
    isDefault?: boolean;
    ttip?: string;
    submenu?: MenuItem[];
    style?: React.CSSProperties;
    url?: string;
    dataset?: object;
}

interface OverrideTheme {
    menu_background: string;
    txc_inactive: string;
    txc_active: string;
    option_active: string;
}

interface ThemeExtended extends Theme {
    // base: string;
    // primaryColor: string;
    // backgroundColor: string; 
    // secondaryBackgroundColor: string;
    // textColor: string;
    // font: string;
    
    // Parámetros adicionales marcados con *
    widgetBackgroundColor?: string;
    widgetBorderColor?: string;
    skeletonBackgroundColor?: string;
    bodyFont?: string;
    codeFont?: string;
    fontFaces?: Array<{
        family: string;
        url: string;
        weight: number;
    }>;
    radii?: {
        checkboxRadius: number;
        baseWidgetRadius: number;
    };
    fontSizes?: {
        tinyFontSize: number;
        smallFontSize: number;
        baseFontSize: number;
    };
}

interface ThemeData {
    name: string;
    icon: string;
    themeInfo: ThemeExtended;
}

type PositionMode = "top" | "under" | "side";

interface PythonArgs {
    menu_definition: MenuItem[];
    home: MenuItem;
    login: MenuItem;
    override_theme: OverrideTheme;
    position_mode: PositionMode;
    is_sticky: boolean;
    styles: string;
    custom_styles: string;
    is_navigation: boolean;
    default_page_selected_id: string;
    override_page_selected_id?: string;
    override_first_page_load_id?: string;
    reclick_load?: boolean;
    prefix_url?: string;
    url_navigation?: boolean;
    key?: string;
    fvalue?: boolean;
    // Si se pasa una lista de ThemeInfo se muestra el boton de cambio de tema dependiendo del numero de elementos
    themes_data?: ThemeData[];
    theme_changer?: boolean;
    collapsible?: boolean;
    is_visible?: boolean;
}

// interface NavBarRenderData extends RenderData {
//   args: PythonArgs;
//   disabled: boolean;
//   theme?: Theme;
// }

interface State {
    selectedPageId: string | null;
    expandState: boolean;
    selectedSubMenu: string | null;
    expandSubMenu: boolean;
    fromClick: boolean;
    themeIndex: number;
    isVisible?: boolean;
}

class StreamlitComponentBase<S = {}> extends React.PureComponent<ComponentProps, S> {
    public componentDidMount(): void {
        // After we're rendered for the first time, tell Streamlit that our height has changed.
        Streamlit.setFrameHeight();
    }

    public componentDidUpdate(prevProps: ComponentProps, prevState: Readonly<S>, snapshot?: any): void {
        // After we're updated, tell Streamlit that our height may have changed.
        Streamlit.setFrameHeight();
    }
}

class NativeNavBar extends StreamlitComponentBase<State> {
    theme: Theme;
    maxNavBarWidth: number = 0;
    resizeTimeout: NodeJS.Timeout | null = null;
    key: string;
    state: State;

    themes_data: ThemeData[] = [];

    public constructor(props: ComponentProps) {
        super(props);
        const args: PythonArgs = props.args;

        let selectedPageId = null;
        let expandState = args.collapsible ? false : true;
        let selectedSubMenu = null;
        let expandSubMenu = false;

        if (args.is_navigation) {
          let bodyPageId = window.parent.document.body.dataset.pageId;
          selectedPageId = bodyPageId;
          if (bodyPageId === "null" || bodyPageId === "undefined" || bodyPageId === undefined) {
              selectedPageId = args.default_page_selected_id;
              if (args.override_first_page_load_id) {
                    selectedPageId = args.override_first_page_load_id;
              }
          }
          expandState = args.collapsible ? false : true;
          selectedSubMenu = window.parent.document.body.dataset.selectedSubMenu === "null" ? null : window.parent.document.body.dataset.selectedSubMenu || null;
          expandSubMenu = window.parent.document.body.dataset.expandSubMenu === 'true' ? true : false;
        }
        else {
          selectedPageId = args.default_page_selected_id;
        }

        if (args.url_navigation) {
            // Si se usa navegación por URL, se obtiene el id de la página desde la URL
            selectedPageId = this.getPageFromURL();
            this.postNavbarState(selectedPageId, expandSubMenu, selectedSubMenu);
            Streamlit.setComponentValue(selectedPageId);
        }
        else if (args.override_page_selected_id) {
            selectedPageId = args.override_page_selected_id;
            this.postNavbarState(selectedPageId, expandSubMenu, selectedSubMenu);
            Streamlit.setComponentValue(selectedPageId);
        }

        // console.debug("Constructor", selectedPageId, args.override_page_selected_id, args.default_page_selected_id);

        this.state = {
            selectedPageId: selectedPageId || args.default_page_selected_id,
            selectedSubMenu: selectedSubMenu,
            expandState: expandState,
            expandSubMenu: expandSubMenu,
            fromClick: false,
            themeIndex: 0,
            isVisible: args.is_visible !== false
        };

        // if (!renderData) {
        //   return <div style={{ color: "red" }}>No hay renderData definida.</div>;
        // }

        // Streamlit sends us a theme object via renderData that we can use to ensure
        // that our component has visuals that match the active theme in a
        // streamlit app.
        let theme: Theme | undefined = this.props.theme;

        // Maintain compatibility with older versions of Streamlit that don't send
        // a theme object.
        if (!theme) {
            // return (
            //     <div style={{ color: "red" }}>
            //     Theme is undefined, please check streamlit version.
            //     </div>
            // );
            theme = {
                base: "light",
                backgroundColor: "#FFFFFF",
                textColor: "#31333F",
                primaryColor: "#FF4B4B",
                secondaryBackgroundColor: "#F0F2F6",
                font: "Sans serif"
            }
        }
        this.theme = theme;

        this.key = this.props.args.key;
        if (this.key === undefined) this.key = `${Date.now()}`;

        // Loads themes from python args. If not, use default themes
        this.themes_data = args.themes_data || this.themes_data;
    }

    postMessage(COI_method: string,
        data?: {
            isExpanded?: boolean,
            themeData?: ThemeData | null,
            pageId?: string | null,
            expandSubMenu?: boolean,
            selectedSubMenu?: string | null,
            iframePositionMode?: string,
            positionMode?: string,
            isNavigation?: boolean,
            isSticky?: boolean,
            styles?: string,
            customStyles?: string,
            currentPageName?: string,
            currentPageScriptHash?: string,
            isDefault?: boolean,
            iframeHeight?: number
        }): boolean {
        const { key } = this.props.args;
        if (key == null || typeof key !== "string") {
            throw new Error("Invalid key: key must be a string.");
        }
        window.parent.postMessage({ COI_method, key, ...data }, "*");

        // console.debug("postMessage from ", key, ": ", COI_method, data);
        return true;
    }
    postRegister(positionMode: string, isSticky: boolean, isExpanded: boolean, themeData?: ThemeData | null): void {
        this.postMessage("register", { positionMode, isSticky, isExpanded, themeData });
    }
    // postUpdateConfig(): void {
    //     let styles = this.styles;
    //     let disable_scroll = this.disable_scroll;
    //     this.postMessage("updateConfig", { styles, disable_scroll });
    // }
    
    // Ejemplos para mas formas de comunicar

    // postScroll(anchor_id: string): void {
    //     this.postMessage("scroll", { anchor_id });
    // }
    
    // postUpdateActiveAnchor(anchor_id: string): void {
    //     const { auto_update_anchor } = this.getCleanedArgs();
    //     if (auto_update_anchor)
    //         this.postMessage("updateActiveAnchor", { anchor_id });
    // }
    postSidebarGetState(): void {
        this.postMessage("sidebarRequestInfo", {});
    }
    postSidebarToggle(positionMode: string, isExpanded: boolean): void {
        this.postMessage("sidebarToggle", { positionMode, isExpanded });
    }
    postThemeToggle(themeData: ThemeData): void {
        this.saveTheme(themeData);
        this.postMessage("themeToggle", { themeData: themeData });
    }
    postNavbarState(pageId: string | null, expandSubMenu: boolean, selectedSubMenu: string | null): void {
        this.postMessage("navbarState", { pageId, expandSubMenu, selectedSubMenu });
    }
    postIframeState(positionMode: string, isSticky: boolean): void {
        this.postMessage("iframeState", { iframePositionMode: positionMode, isSticky, iframeHeight: document.body.scrollHeight });
    }
    postSetStyles(styles: string, customStyles: string): void {
        // Recuperamos el contenido de los estilos de public
        this.postMessage("setStyles", { styles, customStyles });
    }
    private saveTheme(theme_data: ThemeData): void {
        localStorage.setItem('stPluginsActiveTheme-/-v1', JSON.stringify(theme_data));
    }

    // Handle messages from COI
    // Send and Recieved data with custom message not Streamlit Value
    private handleCOIMessage(event: MessageEvent) {
        const { COMPONENT_method, key } = event.data;
        // Check if message is for this component
        if (COMPONENT_method == null || key == null) {
            return;
        }
        if (key !== this.props.args.key) {
            return;
        }

        if (COMPONENT_method === "setReadyRegistered") {
            // Se vuelve a visualizar el navbar al recibir el mensaje de setReadyRegistered
            this.setState({
                isVisible: true
            });
        }
        // console.debug("handleMessage", event.data);
        else if (COMPONENT_method === "sidebarResponseInfo" && this.props.args.position_mode === "side") {
            const { isSideOpen, pageId, expandSubMenu, selectedSubMenu } = event.data;
            // console.debug(key, "sidebarResponseInfo: ", "Received sidebarResponseInfo message with expandState: ", isSideOpen);
            this.setState({
                expandState: isSideOpen,
                selectedPageId: pageId === "null" ? null : this.state.selectedPageId || this.state.selectedPageId,
                expandSubMenu: expandSubMenu || this.state.expandSubMenu,
                selectedSubMenu: selectedSubMenu || this.state.selectedSubMenu
            });
        }
        else if (COMPONENT_method === "setVisualPageId") {
            const { pageId } = event.data;
            // console.debug(key, "setVisualPageId: ", "Received setVisualPageId message with pageId: ", pageId);
            this.setState({ selectedPageId: pageId });
        }
        // if (COMPONENT_method === "updateActiveAnchor") {
        //     const { anchor_id, update_id } = event.data;
        //     console.debug(key, "updateActiveAnchor: ", "Received updateActiveAnchor message with anchor_id: ", anchor_id, "update_id: ", update_id);
        //     //validate anchor_id and debug error if invalid
        //     if (anchor_id == null || typeof anchor_id !== "string") {
        //         console.error("Invalid anchor_id: anchor_id must be a string.");
        //         return;
        //     }
        //     //Validate updateId as number and debug error if invalid
        //     if (update_id == null || typeof update_id !== "number") {
        //         console.error("Invalid updateId: updateId must be a number.");
        //         return;
        //     }

        //     const { auto_update_anchor } = this.getCleanedArgs();
        //     //If auto_update_anchor is false, do not update the active anchor from external source
        //     if (!auto_update_anchor) {
        //         return;
        //     }

        //     //Check if the updateId is the latest
        //     if (update_id > this.updateId) {
        //         this.setState({ activeAnchorId: anchor_id });
        //         console.debug(key, "updateActiveAnchor: ", "Updating `active` anchor to ", anchor_id);
        //         this.updateId = update_id;
        //     }
        //     else {
        //         console.debug("Ignoring updateActiveAnchor message with outdated updateId");
        //     }

        //     // Send back to Streamlit.
        //     Streamlit.setComponentValue(anchor_id);
        // }
    }

    public componentDidMount = () => {
        // console.debug(
        //     "DidMount",
        //     this.state.selectedPageId, this.props.args.override_page_selected_id, this.props.args.default_page_selected_id,
        //     this.state.fromClick
        // );
        let args: PythonArgs = this.props.args;

        // useEffect resize
        this.resizeNavbar(true, false);
        if (args.position_mode !== "side") {
            this.calculateMaxNavBarWidth();
        }
        window.addEventListener("resize", this.handleResize);

        // useEffect functions to detect clicks outside the iframe
        window.addEventListener("blur", this.handleBlur);
        document.addEventListener("click", this.handleClickOutside);

        // Listen for messages from COI
        // No se necesita recibir mensajes de streamlit al componente
        window.addEventListener("message", this.handleCOIMessage.bind(this));

        // Se registran los eventos de COI
        // Register component
        this.postRegister(
          args.position_mode,
          args.is_sticky,
          this.state.expandState,
          args.theme_changer ? this.themes_data[this.state.themeIndex] : null
        );
        // Se acumulan estos eventos para despues procesarlos cuando se termine de montar
        this.postSetStyles(args.styles, args.custom_styles);
        this.postIframeState(args.position_mode, args.is_sticky);
        this.postSidebarGetState();

        // Send styles to COI
        // this.postUpdateConfig();
        // Tell COI to track anchors for visibility
        // this.postTrackAnchors(anchor_ids);
        // Set initial active anchor for component and COI
        // this.setState({ activeAnchorId: initialAnchorId });
        // this.postUpdateActiveAnchor(anchor_ids[0]);

        // Loads themes from python args. If not, use default themes
        this.themes_data = args.themes_data || this.themes_data;
        if (!args.theme_changer) {
          this.themes_data = []
        }

        if (!args.theme_changer || this.themes_data.length === 0) {
            // Si no hay themes_data o no se ha pasado el theme_changer, se oculta el boton de cambio de tema
            return;
        }
        let theme_data_raw = localStorage.getItem('stPluginsActiveTheme-/-v1');
        if (theme_data_raw) {
            let theme_data = JSON.parse(theme_data_raw);
            // Se busca en los themes_info actuales si existe el theme guardado y si no se inicia a 0 el indice
            // y se carga el theme 0 del array de themes_info, sino se deja el de streamlit, es decir no se hace nada
            let themeIndex = this.themes_data.findIndex((theme) => theme.name === theme_data.name);
            if (themeIndex === -1) themeIndex = 0;
            this.setState({ themeIndex: themeIndex });
            this.postThemeToggle(this.themes_data[themeIndex]);
        }
    }

    public componentDidUpdate = (prevProps: ComponentProps, prevState: State, snapshot?: any): void => {
        // Han cambiado los argumentos de PythonArgs sin hacer el DidMount
        // Si se llama desde python programaticamente
        const args: PythonArgs = this.props.args

        let selectedPageId = this.state.selectedPageId;
        // let prevselectedPageId = prevState.selectedPageId;

        let argDefault = args.default_page_selected_id;
        let prevArgDefault = prevProps.args.default_page_selected_id;
        let argOverride = args.override_page_selected_id;
        let prevArgOverride = prevProps.args.override_page_selected_id;

        // console.debug(
        //     "DidUpdate",
        //     this.state.selectedPageId, this.props.args.override_page_selected_id, this.props.args.default_page_selected_id,
        //     this.state.fromClick
        // );
        if (args.position_mode !== prevProps.args.position_mode || args.is_sticky !== prevProps.args.is_sticky) {
            this.postIframeState(args.position_mode, args.is_sticky);
            this.postSetStyles(args.styles, args.custom_styles);
        }

        if (prevArgDefault !== argDefault || prevArgOverride !== argOverride) {
            selectedPageId = this.state.selectedPageId;

            // console.log(
            //     "Props DidUpdate",
            //     this.state.selectedPageId, this.props.args.override_page_selected_id, this.props.args.default_page_selected_id,
            //     this.state.fromClick
            // );
            if (argOverride) {
                selectedPageId = argOverride || argDefault;

                this.setState(
                    {
                        selectedPageId: selectedPageId,
                        selectedSubMenu: this.state.selectedSubMenu,
                        expandState: this.state.expandState,
                        expandSubMenu: this.state.expandSubMenu,
                        fromClick: false,
                        themeIndex: this.state.themeIndex
                    },
                    () => {
                        this.resizeNavbar(true);
                        if (prevArgOverride !== argOverride) {
                            this.postNavbarState(selectedPageId, this.state.expandSubMenu, this.state.selectedSubMenu);
                            Streamlit.setComponentValue(selectedPageId);
                        }
                    }
                );
            }
        }

        // Loads themes from python args. If not, use default themes
        this.themes_data = this.props.args.themes_data || this.themes_data;
        // Se busca en los themes_info actuales si existe el theme guardado y si no se inicia a 0 el indice
        // y se carga el theme 0 del array de themes_info, sino se deja el de streamlit, es decir no se hace nada
        if (this.props.args.theme_changer && this.themes_data.length > 0) {
          this.saveTheme(this.themes_data[this.state.themeIndex]);
        }
    }

    public componentWillUnmount = () => {
        this.postNavbarState(this.state.selectedPageId, this.state.expandSubMenu, this.state.selectedSubMenu);

        // console.debug("Unmount", this.state.selectedPageId);

        // useEffect resize
        window.removeEventListener("resize", this.handleResize);

        // useEffect functions to detect clicks outside the iframe
        window.removeEventListener("blur", this.handleBlur);
        document.removeEventListener("click", this.handleClickOutside);

        // Streamlit.setFrameHeight();
    }

    /* Functions definition */
    private getPageFromURL = (): string => {
        const url = new URL(window.parent.location.href);
        let path = url.pathname.replace(/^\/+|\/+$/g, "");
        if (this.props.args.prefix_url) {
            const prefix = this.props.args.prefix_url.replace(/^\/+|\/+$/g, "");
            if (path.startsWith(prefix)) {
                path = path.slice(prefix.length).replace(/^\/+/, "");
            }
        }

        // Si el path está vacío, devuelve la página por defecto
        if (!path) {
            return this.props.args.default_page_selected_id;
        }

        // Busca el item del menú o submenú que coincida con el path
        const menuItems = this.props.args.menu_definition;
        function findMenuItemByPath(items: MenuItem[]): MenuItem | undefined {
            for (const item of items) {
                if (item.url === path || item.url === "/" + path) {
                    return item;
                }
                if (item.submenu) {
                    const found = findMenuItemByPath(item.submenu);
                    if (found) return found;
                }
            }
            return undefined;
        }
        const match = findMenuItemByPath(menuItems);
        if (match) {
            return match.id;
        }

        // Si no hay coincidencia, devuelve la página por defecto
        return this.props.args.default_page_selected_id;
    }

    private calculateMaxNavBarWidth = () => {
        const navbar$ = document.querySelector(`nav.navbar#navbar-${this.key}`) as HTMLElement;
        if (navbar$ === null) return;

        const container$ = navbar$.querySelector(".navbar-wrapper") as HTMLElement;
        if (container$ === null) return;

        const listItems$ = container$.querySelectorAll(":scope > ul > li") as NodeListOf<HTMLElement>;
        if (listItems$.length === 0) return;

        container$.classList.add("nav-open");

        let totalWidth = 0;
        listItems$.forEach((li) => {
            totalWidth += li.clientWidth;
        });
        let themeToggle$ = navbar$.querySelector(".theme-toggler") as HTMLElement;
        if (themeToggle$ !== null) {
            totalWidth += themeToggle$.clientWidth;
        }

        container$.classList.remove("nav-open");
        this.maxNavBarWidth = totalWidth;
    }
    private checkNavbarOverflow = () => {
        const navbar$ = document.querySelector(`nav.navbar#navbar-${this.key}`) as HTMLElement;
        if (navbar$ === null) return;

        let navBarWidth = navbar$.clientWidth;

        if (navBarWidth < this.maxNavBarWidth) {
            navbar$.classList.add('collapsed');
        } else {
            navbar$.classList.remove('collapsed');
        }
    };

    private handleClickOutside = (event: MouseEvent) => {
        // Si es modo side no se cierra el navbar
        if (this.props.args.position_mode === "side") return;
        if (!document.hasFocus()) {
            this.setState(
                {
                    selectedPageId: this.state.selectedPageId,
                    selectedSubMenu: this.state.selectedSubMenu,
                    expandState: false,
                    expandSubMenu: false,
                    fromClick: false,
                    themeIndex: this.state.themeIndex
                },
                () => this.delayed_resize(50)
            );
        }
    };

    private handleBlur = () => {
        // Si es modo side no se cierra el navbar
        if (this.props.args.position_mode === "side") return;
        this.setState(
            {
                selectedPageId: this.state.selectedPageId,
                selectedSubMenu: this.state.selectedSubMenu,
                expandState: false,
                expandSubMenu: false,
                fromClick: false,
                themeIndex: this.state.themeIndex
            },
            () => this.delayed_resize(50)
        );
    };
    private resizeNavbar = (changeNow: boolean = false, postIframe: boolean = true) => {
        this.handleResize();
        if (changeNow) {
            Streamlit.setFrameHeight();
            if (postIframe) this.postIframeState(this.props.args.position_mode, this.props.args.is_sticky);
        }
    }
    private handleResize = () => {
        if (this.resizeTimeout) {
            clearTimeout(this.resizeTimeout);
        }
        this.resizeTimeout = setTimeout(() => {
            if (this.props.args.position_mode !== "side") {
                this.checkNavbarOverflow();
            }
            Streamlit.setFrameHeight();
        }, 200);
    };

    private delayed_resize = (wait_time: number): NodeJS.Timeout => {
        return setTimeout(() => {
            Streamlit.setFrameHeight();
            this.postIframeState(this.props.args.position_mode, this.props.args.is_sticky);
        }, wait_time);
    };

    private containsEmojis = (input: string): boolean => {
        if (input) {
            for (const c of input) {
                const cHex = c.codePointAt(0);
                if (cHex) {
                    const sHex = cHex.toString(16);
                    const lHex = sHex.length;
                    if (lHex > 3) {
                        const prefix = sHex.substring(0, 2);

                        if (lHex === 5 && prefix === "1f") {
                            return true;
                        }

                        if (lHex === 4) {
                            return (
                                ["20", "21", "23", "24", "25", "26", "27", "2B", "29", "30", "32"].indexOf(prefix) > -1
                            );
                        }
                    }
                }
            }
        }
        return false;
    };

    private addHomeLogin = (): MenuItem[] => {
        const args: PythonArgs = this.props.args;
        const menuItems = [...args.menu_definition];
        if (args.home) {
            menuItems.unshift(args.home);
        }
        if (args.login) {
            menuItems.push({ ...args.login, dataset: { login: true } });
        }
        return menuItems;
    };

    private clickOnPage = (item: MenuItem): void => {
        let prevselectedPageId = this.state.selectedPageId;
        let itemId = item.id;
        this.setState(
            {
                selectedPageId: itemId,
                selectedSubMenu: this.state.selectedSubMenu,
                expandState: this.state.expandState,
                expandSubMenu: this.state.expandSubMenu,
                fromClick: true,
                themeIndex: this.state.themeIndex
            },
            () => {
                this.resizeNavbar(true);
                let args: PythonArgs = this.props.args;
                if (prevselectedPageId !== itemId || args.reclick_load) {
                    this.postNavbarState(itemId, this.state.expandSubMenu, this.state.selectedSubMenu);
                    Streamlit.setComponentValue(itemId);
                    // Buscar de forma recursiva la URL del item seleccionado
                    let currentPageName = item.label;
                    let currentPageScriptHash = item.id;
                    let isDefault = args.default_page_selected_id === itemId;
                    this.postMessage("setCurrentPage", { currentPageName, currentPageScriptHash, isDefault });
                }
            }
        );
    };

    private toggleSubMenu = (parentId: string): void => {
        let selectedSubMenu = this.state.selectedSubMenu;
        let expandSubMenu = this.state.expandSubMenu;
        if (this.state.selectedSubMenu === parentId) {
            expandSubMenu = !expandSubMenu;
        }
        else {
            expandSubMenu = true;
            selectedSubMenu = parentId;
        }
        if (!expandSubMenu) selectedSubMenu = null;
        this.setState(
            {
                selectedPageId: this.state.selectedPageId,
                selectedSubMenu: selectedSubMenu,
                expandState: this.state.expandState,
                expandSubMenu: expandSubMenu,
                fromClick: false,
                themeIndex: this.state.themeIndex
            },
            () => {
                this.resizeNavbar(true);
                this.postNavbarState(this.state.selectedPageId, expandSubMenu, selectedSubMenu);
            }
        );

    };

    private createSubMenu = (parent_id: string, item: MenuItem, key: number): JSX.Element => (
        <NavSubItem
            subitem={item}
            menu_id={key}
            submenu_toggle={this.toggleSubMenu}
            click_on_app={this.clickOnPage}
            parent_id={parent_id}
            key={key}
            is_active={item.id === this.state.selectedPageId}
        />
    );

    private toggleNav = (): void => {
        // let expandState = this.state.expandState ? "nav-close" : "nav-open"
        let args: PythonArgs = this.props.args;
        this.setState(
            {
                selectedPageId: this.state.selectedPageId,
                selectedSubMenu: this.state.selectedSubMenu,
                expandState: !this.state.expandState,
                expandSubMenu: args.position_mode === "side" ? this.state.expandSubMenu : false,
                fromClick: false,
                themeIndex: this.state.themeIndex
            },
            () => {
                this.resizeNavbar(true);
                if (args.position_mode === "side") this.postSidebarToggle(args.position_mode, this.state.expandState);
            }
        );
    };

    private themeToggle = (): void => {
        this.setState({ 
            themeIndex: (this.state.themeIndex + 1) % this.themes_data.length 
        },
        () => {
            this.postThemeToggle(this.themes_data[this.state.themeIndex]);
        });
    }

    private createMenu = (item: MenuItem, key: number): JSX.Element => {
        const isActive = item.id === this.state.selectedPageId;
        const hasIcon = item.icon ? true : false;

        // Me quedo con la primera letra de label para el icono en mayuscula
        let iconContent = ""
        if (this.props.args.position_mode === "side") {
            iconContent = item.label.charAt(0).toUpperCase()
        }
        let iconMarkup = <span className="icon icon-placeholder">{iconContent}</span>;

        // Determinar si se usa <i> o <span> para el icono
        if (hasIcon) {
            const regex = /:material\/(\w+):/gm;
            const m = regex.exec(item.icon);
            if (m !== null) {
                const symbol = m[1];
                iconMarkup = <span className="material-symbols-rounded icon">{symbol}</span>;
            }
            else {
                const iconClass = this.containsEmojis(item.icon) ? "icon" : `${item.icon} icon`;
                const iconTxt = this.containsEmojis(item.icon) ? item.icon : "";
                iconMarkup = <i className={iconClass}>{iconTxt}</i>;
            }
        }
        // Construir los atributos data-* a partir de item.dataset
        const dataAttributes = item.dataset ? Object.entries(item.dataset).reduce((acc, [key, value]) => {
            acc[`data-${key}`] = value;
            return acc;
        }, {} as { [key: string]: any }) : {};

        if (item.submenu) {
            return (
                <li
                    style={item.style}
                    className={`nav-item py-0 dropdown ${isActive ? "active" : ""}`}
                    key={key * 100}
                    {...dataAttributes}
                >
                    <a
                        className="nav-link dropdown-toggle"
                        href={"#_sub" + key}
                        key={"sub1_" + key}
                        onClick={() => this.toggleSubMenu(item.id)}
                        data-toggle="tooltip"
                        data-placement="top"
                        data-html="true"
                        title={item.ttip}
                    >
                        {iconMarkup}
                        <span>{item.label}</span>
                    </a>
                    <ul key={key * 103} className={`dropdown-menu ${this.state.selectedSubMenu === item.id && this.state.expandSubMenu ? "show" : ""}`}>
                        {item.submenu.map((subitem: MenuItem, subindex: number) => this.createSubMenu(item.id, subitem, subindex))}
                    </ul>
                </li>
            );
        }
        else {
            return (
                <NavItem
                    menuitem={item}
                    menu_id={key}
                    position_mode={this.props.args.position_mode}
                    is_active={isActive}
                    submenu_toggle={this.toggleSubMenu}
                    click_on_app={this.clickOnPage}
                    key={key * 104}
                    dataAttributes={dataAttributes}
                />
            );
        }
    };

    private applyNavTheme = (): ReactNode => {
        const args: PythonArgs = this.props.args;

        const mergedTheme = {
            menu_background: this.theme.backgroundColor,
            txc_inactive: this.theme.textColor,
            txc_active: this.theme.textColor,
            option_active: this.theme.primaryColor
        };

        const overrideTheme = args.override_theme;
        if (overrideTheme) {
            mergedTheme.menu_background = overrideTheme.menu_background || mergedTheme.menu_background;
            mergedTheme.txc_inactive = overrideTheme.txc_inactive || mergedTheme.txc_inactive;
            mergedTheme.txc_active = overrideTheme.txc_active || mergedTheme.txc_active;
            mergedTheme.option_active = overrideTheme.option_active || mergedTheme.option_active;
        }

        return (
            <style>
                {`
            :root {
                --menu_background: ${mergedTheme.menu_background};
                --txc_inactive: ${mergedTheme.txc_inactive};
                --txc_active: ${mergedTheme.txc_active};
                --option_active: ${mergedTheme.option_active};
                --option_active_opacity: ${this.theme.primaryColor}99;
                --option_active_translucent: ${this.theme.primaryColor}38;
            }
            `}
            </style>
        );
    };

    public render = (): ReactNode => {
        const args: PythonArgs = this.props.args;

        const menuItems = this.addHomeLogin();
        const positionMode = args.position_mode;
        const currentTheme = this.themes_data[this.state.themeIndex];
        const themeIcon = currentTheme?.icon || "format_paint";
        const themeTooltip = currentTheme?.name || "Toogle theme";

        const navbarId = `navbar-${this.key}`
        return (
            <StyletronProvider value={engine}>
                <BaseProvider theme={LightTheme}>
                    <div key={args.key}>
                        {this.applyNavTheme()}
                        <nav id={navbarId} className={`navbar navbar-expand-custom navbar-mainbg py-0 py-md-0 ${positionMode}`}>
                            <button
                                className="navbar-toggler"
                                type="button"
                                onClick={this.toggleNav}
                                aria-expanded={this.state.expandState}
                            >
                                <span className="material-symbols-rounded text-color menu-closed">menu</span>
                                <span className="material-symbols-rounded text-color menu-open">menu_open</span>
                            </button>
                            <div className={`navbar-collapse navbar-wrapper ${this.state.expandState ? "nav-open" : "nav-close"}`}>
                                <ul className="navbar-nav py-0">
                                    {menuItems.map((item: MenuItem, index: number) => this.createMenu(item, index))}
                                </ul>
                            </div>
                            {this.themes_data && this.themes_data.length > 0 && (
                                <button
                                    className="theme-toggler"
                                    type="button"
                                    onClick={this.themeToggle}
                                    title={themeTooltip}
                                >
                                    <span className="material-symbols-rounded text-color">{themeIcon}</span>
                                </button>
                            )}
                        </nav>
                    </div>
                </BaseProvider>
            </StyletronProvider>
        );
    };

    // return render();
};

export default withStreamlitConnection(NativeNavBar);
// export default NativeNavBar;
