/**
 * Live kamera — H.265 RTSP kameralar uchun to'liq fallback zanjiri:
 * 1) WebSocket: webrtc/tcp → webrtc → mse → mjpeg (edge server transcode)
 * 2) Snapshot polling (har doim ishlaydi, agar edge snapshot bersa)
 */
const WS_SCHEME = location.protocol === "https:" ? "wss" : "ws";

function getStreamHost() {
    // Har doim joriy sayt hosti — nginx orqali proxy (CORS/auth muammosiz)
    return location.host;
}

function buildWsUrl(token) {
    const url = new URL(`${WS_SCHEME}://${getStreamHost()}/camera/stream/`, location.href);
    url.searchParams.set("token", token);
    return url.href;
}

function isStreamError(text) {
    if (!text) return false;
    const t = text.toLowerCase();
    return t.includes("error") || t.includes("codecs not matched") || t.includes("failed");
}

/**
 * Snapshot polling — H.265 uchun ishonchli fallback (~2 FPS).
 */
function startSnapshotLive(shell, frameUrl, onStatus) {
    shell.innerHTML = "";
    const wrap = document.createElement("div");
    wrap.className = "w-100 position-relative";
    wrap.style.background = "#0f172a";
    wrap.style.minHeight = "360px";

    const img = document.createElement("img");
    img.className = "w-100 d-block";
    img.alt = "live";
    img.style.minHeight = "240px";
    img.style.objectFit = "contain";

    const badge = document.createElement("div");
    badge.className = "position-absolute top-0 end-0 m-2 badge text-bg-secondary";
    badge.textContent = "SNAPSHOT";

    const hint = document.createElement("p");
    hint.className = "small text-white-50 text-center mb-0 py-2";
    hint.textContent = typeof gettext === "function"
        ? gettext("RTSP H.265 — to'liq video uchun edge serverda ffmpeg/H.264 substream sozlang.")
        : "RTSP H.265 — edge serverda ffmpeg yoki H.264 substream kerak.";

    wrap.appendChild(img);
    wrap.appendChild(badge);
    shell.appendChild(wrap);
    shell.appendChild(hint);

    let active = true;
    let busy = false;

    async function tick() {
        if (!active || busy) return;
        busy = true;
        try {
            const url = new URL(frameUrl, location.href);
            url.searchParams.set("_", String(Date.now()));
            const resp = await fetch(url.href, {
                cache: "no-store",
                credentials: "same-origin",
            });
            if (!resp.ok) throw new Error("frame");
            const blob = await resp.blob();
            const old = img.dataset.blobUrl;
            img.src = URL.createObjectURL(blob);
            if (old) URL.revokeObjectURL(old);
            img.dataset.blobUrl = img.src;
            onStatus?.("SNAPSHOT");
        } catch (e) {
            onStatus?.("…");
        } finally {
            busy = false;
            if (active) setTimeout(tick, 500);
        }
    }

    tick();
    return () => { active = false; };
}

/**
 * go2rtc video-stream (WebSocket).
 */
function startWebRtcStream(shell, token, onStatus, onFatal) {
    shell.innerHTML = "";
    const wrap = document.createElement("div");
    wrap.className = "w-100";
    shell.appendChild(wrap);

    const el = document.createElement("video-stream");
    el.mode = "webrtc/tcp,webrtc,mse,mjpeg";
    el.media = "video";
    el.background = false;
    el.visibilityCheck = false;
    el.src = buildWsUrl(token);
    wrap.appendChild(el);

    let stopped = false;
    let fallbackScheduled = false;

    const scheduleFallback = (reason) => {
        if (fallbackScheduled || stopped) return;
        fallbackScheduled = true;
        console.warn("[live] fallback:", reason);
        try { el.disconnectedCallback?.(); } catch (e) { /* ignore */ }
        onFatal?.(reason);
    };

    const poll = setInterval(() => {
        if (stopped) {
            clearInterval(poll);
            return;
        }
        const mode = el.querySelector(".mode")?.innerText || "";
        const status = el.querySelector(".status")?.innerText || "";
        if (mode && mode !== "loading" && mode !== "error") {
            onStatus?.(mode);
        }
        if (isStreamError(status) || mode === "error") {
            clearInterval(poll);
            scheduleFallback(status || mode);
        }
    }, 1500);

    setTimeout(() => {
        if (stopped || fallbackScheduled) return;
        const mode = el.querySelector(".mode")?.innerText || "";
        if (!mode || mode === "loading") {
            scheduleFallback("timeout");
        }
    }, 15000);

    return () => {
        stopped = true;
        clearInterval(poll);
        try { el.disconnectedCallback?.(); } catch (e) { /* ignore */ }
    };
}

/**
 * @param {string} token — imzolangan hall_id|device_sn
 * @param {HTMLElement|null} container
 * @param {{frameUrl?: string}} options
 */
function init_stream(token, container = null, options = {}) {
    const root = container || document.querySelector(".video-shell");
    if (!root) return null;

    if (root.querySelector(".spinner-border")) {
        root.innerHTML = "";
    }

    const frameUrl = options.frameUrl || null;
    let stopWs = null;
    let stopSnap = null;

    let player = root.querySelector(".live-player");
    if (!player) {
        player = document.createElement("div");
        player.className = "w-100 live-player";
        root.appendChild(player);
    }

    let statusEl = root.querySelector(".live-status");
    if (!statusEl) {
        statusEl = document.createElement("div");
        statusEl.className = "small text-white-50 text-center py-1 live-status";
        root.appendChild(statusEl);
    }
    statusEl.textContent = typeof gettext === "function" ? gettext("Ulanmoqda...") : "Ulanmoqda...";

    const setStatus = (text) => {
        statusEl.textContent = text || "";
    };

    const startSnap = () => {
        if (!frameUrl) {
            setStatus(typeof gettext === "function" ? gettext("Live stream ishlamadi") : "Live stream ishlamadi");
            return;
        }
        stopWs?.();
        stopWs = null;
        if (stopSnap) return;
        stopSnap = startSnapshotLive(player, frameUrl, setStatus);
    };

    stopWs = startWebRtcStream(player, token, setStatus, () => startSnap());

    return () => {
        stopWs?.();
        stopSnap?.();
    };
}

if (typeof window !== "undefined") {
    window.init_stream = init_stream;
}
