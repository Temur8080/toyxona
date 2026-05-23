/**
 * Live kamera — SmartBozor uslubi: go2rtc video-stream + WebRTC birinchi.
 * VPN uchun webrtc/tcp; xato bo'lsa snapshot fallback (~1 FPS).
 */
const WS_SCHEME = location.protocol === "https:" ? "wss" : "ws";

function buildWsUrl(token) {
    const url = new URL(`${WS_SCHEME}://${location.host}/camera/stream/`, location.href);
    url.searchParams.set("token", token);
    return url.href;
}

function isFatalStreamError(text) {
    if (!text) return false;
    const t = text.toLowerCase();
    return t.includes("codecs not matched")
        || t.includes("failed")
        || (t.includes("error") && !t.includes("loading"));
}

function startSnapshotFallback(root, frameUrl) {
    root.innerHTML = "";
    const wrap = document.createElement("div");
    wrap.className = "w-100 position-relative bg-dark";
    wrap.style.minHeight = "360px";

    const img = document.createElement("img");
    img.className = "w-100 d-block";
    img.alt = "live";
    img.style.objectFit = "contain";
    img.style.minHeight = "240px";

    const badge = document.createElement("div");
    badge.className = "position-absolute top-0 end-0 m-2 badge text-bg-secondary";
    badge.textContent = "SNAPSHOT";

    wrap.appendChild(img);
    wrap.appendChild(badge);
    root.appendChild(wrap);

    let active = true;
    let busy = false;

    async function tick() {
        if (!active || busy) return;
        busy = true;
        try {
            const url = new URL(frameUrl, location.href);
            url.searchParams.set("_", String(Date.now()));
            const resp = await fetch(url.href, { cache: "no-store", credentials: "same-origin" });
            if (!resp.ok) throw new Error("frame");
            const blob = await resp.blob();
            const old = img.dataset.blobUrl;
            img.src = URL.createObjectURL(blob);
            if (old) URL.revokeObjectURL(old);
            img.dataset.blobUrl = img.src;
        } finally {
            busy = false;
            if (active) setTimeout(tick, 1000);
        }
    }

    tick();
    return () => { active = false; };
}

/**
 * @param {string} token
 * @param {HTMLElement|null} container
 * @param {{frameUrl?: string}} options
 */
function init_stream(token, container = null, options = {}) {
    const root = container || document.querySelector(".video-container, .video-shell");
    if (!root) return null;

    root.innerHTML = "";
    const wrap = document.createElement("div");
    wrap.className = "w-100";
    root.appendChild(wrap);

    const el = document.createElement("video-stream");
    el.mode = "webrtc/tcp,webrtc,mse,hls,mjpeg";
    el.media = "video,audio";
    el.background = false;
    el.visibilityCheck = false;
    el.src = buildWsUrl(token);
    wrap.appendChild(el);

    const frameUrl = options.frameUrl || "";
    if (!frameUrl) return el;

    let fallbackDone = false;
    let stopSnap = null;

    const runFallback = () => {
        if (fallbackDone) return;
        fallbackDone = true;
        try { el.disconnectedCallback?.(); } catch (e) { /* ignore */ }
        stopSnap = startSnapshotFallback(root, frameUrl);
    };

    const watch = setInterval(() => {
        const status = el.querySelector(".status")?.innerText || "";
        const mode = el.querySelector(".mode")?.innerText || "";
        if (mode === "error" || isFatalStreamError(status)) {
            clearInterval(watch);
            runFallback();
        }
    }, 2000);

    setTimeout(() => {
        clearInterval(watch);
        if (fallbackDone) return;
        const mode = el.querySelector(".mode")?.innerText || "";
        const status = el.querySelector(".status")?.innerText || "";
        if (mode === "error" || isFatalStreamError(status)) {
            runFallback();
        }
    }, 30000);

    return el;
}

if (typeof window !== "undefined") {
    window.init_stream = init_stream;
}
