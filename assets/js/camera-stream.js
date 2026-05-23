/**
 * Live stream — VPS nginx → Edge go2rtc (VPN).
 * WebRTC orqali ikki hop juda qotadi; MSE/MJPEG barqarorroq.
 */
const wsScheme = location.protocol === "https:" ? "wss" : "ws";
let streamHost = document.currentScript?.getAttribute("data-stream-host");

function init_stream(token, container = null) {
    const host = document.querySelector(".video-shell") || container;
    if (!host) return null;

    host.innerHTML = "";
    const wrap = document.createElement("div");
    wrap.className = "w-100";
    host.appendChild(wrap);

    const el = document.createElement("video-stream");
    el.mode = "mse,mjpeg";
    el.media = "video";
    el.background = false;
    el.visibilityCheck = true;

    if (!streamHost || streamHost.length === 0) {
        streamHost = location.host;
    }

    const url = new URL(`${wsScheme}://${streamHost}/camera/stream/?token=${token}`, location.href);
    el.src = url.href;
    wrap.appendChild(el);
    return el;
}

if (typeof window !== "undefined") {
    window.init_stream = init_stream;
}
