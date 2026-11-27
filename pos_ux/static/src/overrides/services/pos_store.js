import { PosStore } from "@point_of_sale/app/services/pos_store";
import { resetLocalData } from "@point_of_sale/app/components/loader/critical_pos_error/reset_local_data";
import { patch } from "@web/core/utils/patch";
import { ConfirmationDialog, AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";

// Query params kept across the reload, which wipes every local storage.
const RELOADED_PARAM = "pos_ux_reloaded";
const CLOSE_PARAM = "pos_ux_close_after_reload";
// Time the register has to stay free before reloading on its own.
const IDLE_RELOAD_DELAY = 60000;
const IDLE_CHECK_INTERVAL = 10000;

patch(PosStore.prototype, {
    async setup() {
        this.outdatedAssets = false;
        this.idleReloadTimer = null;
        await super.setup(...arguments);
        this.data.connectWebSocket("POS_UX_ASSETS_VERSION", ({ version }) => {
            this.onOutdatedAssets(version);
        });
    },

    getDefaultPartnerId() {
        return this.config.default_partner_id?.id || super.getDefaultPartnerId();
    },

    /**
     * Stamp of the POS files this screen is actually running, read from the
     * script tag the browser loaded. False when it cannot be read (debug
     * assets), where the stamp of the startup is used instead.
     */
    getLoadedAssetsVersion() {
        const scripts = [...document.querySelectorAll("script[src]")];
        const script = scripts.find((s) => s.src.includes("point_of_sale.assets_prod"));
        const unique = script?.src.match(/\/web\/assets\/([^/]+)\//)?.[1];
        return unique && unique !== "debug" ? unique : false;
    },

    async fetchAssetsVersion() {
        if (this.data.network.offline) {
            return false;
        }
        try {
            return await this.data.call("pos.config", "get_pos_assets_version", []);
        } catch {
            return false;
        }
    },

    /**
     * Ask the server for the current stamp and compare it with the one this
     * screen started with.
     */
    async checkAssetsVersion() {
        const version = await this.fetchAssetsVersion();
        if (version && version !== this.startupAssetsVersion) {
            this.onOutdatedAssets(version);
        }
        return this.outdatedAssets;
    },

    onOutdatedAssets(version) {
        if (this.outdatedAssets || version === this.startupAssetsVersion) {
            return;
        }
        this.outdatedAssets = true;
        this.notification.add(_t("A new version of the register is available."), {
            title: _t("Outdated register"),
            type: "warning",
            sticky: true,
            buttons: [
                {
                    name: _t("Update"),
                    primary: true,
                    onClick: () => this.safeFullReload(),
                },
            ],
        });
        this.startIdleReload();
    },

    /**
     * Reload the register with the last version, without losing a paid order.
     * Returns false when the reload cannot be done right now.
     */
    async safeFullReload({ silent = false } = {}) {
        if (this.data.network.offline) {
            if (!silent) {
                this.dialog.add(AlertDialog, {
                    title: _t("No connection"),
                    body: _t(
                        "The register cannot be updated without internet connection, "
                        + "because the update deletes the data that lets it work offline."
                    ),
                });
            }
            return false;
        }

        try {
            await this.syncAllOrders({ throw: true });
        } catch {
            // Handled below: whatever did not reach the server is still pending.
        }

        const pending = this.models["pos.order"].filter((order) => order.isUnsyncedPaid).length
            || this.data.network.unsyncData.length;
        if (pending) {
            if (!silent) {
                this.dialog.add(AlertDialog, {
                    title: _t("Paid orders not sent yet"),
                    body:
                        pending === 1
                            ? _t(
                                  "There is a paid order that did not reach the server. Check "
                                  + "the internet connection and try again: updating now would "
                                  + "lose it."
                              )
                            : _t(
                                  "There are %s paid orders that did not reach the server. Check "
                                  + "the internet connection and try again: updating now would "
                                  + "lose them.",
                                  pending
                              ),
                });
            }
            return false;
        }

        const url = new URL(window.location.href);
        url.searchParams.set(RELOADED_PARAM, (await this.fetchAssetsVersion()) || "1");
        window.history.replaceState({}, "", url);
        await resetLocalData();
        return true;
    },

    askFullReload() {
        this.dialog.add(ConfirmationDialog, {
            title: _t("Update register"),
            body: _t(
                "The register is going to be reloaded with the last version. It may take a few minutes."
            ),
            confirmLabel: _t("Update"),
            confirm: () => this.safeFullReload(),
            cancel: () => {},
        });
    },

    /**
     * Reload on its own once the register stays free for a while, so a sale in
     * progress is never interrupted.
     */
    startIdleReload() {
        if (this.idleReloadTimer) {
            return;
        }
        let freeSince = this.isRegisterFree() ? Date.now() : null;
        this.idleReloadTimer = setInterval(async () => {
            if (!this.isRegisterFree()) {
                freeSince = null;
                return;
            }
            freeSince = freeSince ?? Date.now();
            if (Date.now() - freeSince < IDLE_RELOAD_DELAY) {
                return;
            }
            clearInterval(this.idleReloadTimer);
            this.idleReloadTimer = null;
            if (!(await this.safeFullReload({ silent: true }))) {
                this.startIdleReload();
            }
        }, IDLE_CHECK_INTERVAL);
    },

    isRegisterFree() {
        if (this.router.state.current === "PaymentScreen") {
            return false;
        }
        return this.getOpenOrders().every((order) => order.lines.length === 0);
    },

    async posBackOnline() {
        await super.posBackOnline(...arguments);
        this.checkAssetsVersion();
    },

    async afterProcessServerData() {
        await super.afterProcessServerData(...arguments);
        await this.checkAssetsVersionOnStartup();
        this.resumeCloseAfterReload();
    },

    /**
     * On startup the stamp of the server is compared with the one of the files
     * the browser is running, which may come from its own cache.
     */
    async checkAssetsVersionOnStartup() {
        this.startupAssetsVersion = this.getLoadedAssetsVersion();
        const version = await this.fetchAssetsVersion();
        if (!version || version === this.startupAssetsVersion) {
            return;
        }
        if (!this.startupAssetsVersion) {
            // Debug assets: the running version cannot be read, so only the
            // changes from now on are noticed.
            this.startupAssetsVersion = version;
            return;
        }
        const params = new URLSearchParams(window.location.search);
        if (params.get(RELOADED_PARAM) !== version) {
            await this.safeFullReload({ silent: true });
        }
        // Still here: the reload could not be done, so at least warn about it.
        this.onOutdatedAssets(version);
    },

    /**
     * Resume the close of the register interrupted by an update.
     */
    resumeCloseAfterReload() {
        const url = new URL(window.location.href);
        if (!url.searchParams.get(CLOSE_PARAM)) {
            return;
        }
        url.searchParams.delete(CLOSE_PARAM);
        window.history.replaceState({}, "", url);
        this.closeSession();
    },

    async closeSession() {
        if (await this.checkAssetsVersion()) {
            const url = new URL(window.location.href);
            url.searchParams.set(CLOSE_PARAM, "1");
            window.history.replaceState({}, "", url);
            if (await this.safeFullReload()) {
                return;
            }
            url.searchParams.delete(CLOSE_PARAM);
            window.history.replaceState({}, "", url);
        }
        return await super.closeSession(...arguments);
    },
});
