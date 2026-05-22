const wsScheme = location.protocol === 'https:' ? 'wss' : 'ws';
let streamHost = document.currentScript.getAttribute("data-stream-host");
if (streamHost.length === 0) {
    streamHost = location.hostname;
}
function init_stream(token, container=null) {
    if (!container) {
        container = document.querySelector(".video-container")
    }
    container.innerHTML = ''
    const video = document.createElement('video-stream');
    video.src = new URL(`wss://${streamHost}/camera/stream/?token=${token}`, location.href);
    container.appendChild(video);
    return video
}