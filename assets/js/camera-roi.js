let zoneCounter = 0;

function defaultZoneName() {
    zoneCounter += 1;
    return `zona${zoneCounter}`;
}

function formatRoiErrors(data) {
    if (!data) return gettext("Saqlashda xato");
    if (data.message) return data.message;
    if (data.error) return data.error;
    if (data.errors) {
        try {
            return JSON.stringify(data.errors, null, 2);
        } catch (e) {
            return String(data.errors);
        }
    }
    return gettext("Saqlashda xato");
}

function newRoiId() {
    if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
        return crypto.randomUUID();
    }
    return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, c => {
        const r = Math.random() * 16 | 0;
        const v = c === "x" ? r : (r & 0x3) | 0x8;
        return v.toString(16);
    });
}

const CANVAS_SIZE = {w: 1024, h: 576};
const JSON_ROI_SIZE = {w: 640, h: 360};
const CENTER = {x: CANVAS_SIZE.w / 2, y: CANVAS_SIZE.h / 2};
const POLY_DEFAULT_SIZE = 200;
const SELECTED_FILL = "rgba(255,235,59,0.75)";
const TRANSPARENT = "rgba(255,235,59,0.5)";

let roiJsonFiles = [];
let roiJsonIndex = -1;
let roiReady = false;

const save_el = document.querySelector("#id_saved");
const roi_json_el = document.querySelector("#id_json_roi");
let loading_el = document.querySelector("#id_loading");
const assign_modal_el = document.querySelector("#id_assign_modal");
const assign_modal = assign_modal_el ? new bootstrap.Modal(assign_modal_el) : null;
const canvas_el = document.querySelector("#id-camera-roi");
const canvas = canvas_el ? new fabric.Canvas(canvas_el, {
    width: CANVAS_SIZE.w,
    height: CANVAS_SIZE.h,
}) : null;
const ICONS = {};

function showWorkspace() {
    document.querySelector("#id_roi_canvas_wrap")?.classList.remove("d-none");
    if (loading_el) {
        loading_el.remove();
        loading_el = null;
    }
    roiReady = true;
}

async function load_saved() {
    if (!save_el || !canvas) return;
    const data = JSON.parse(save_el.innerText);
    if (Array.isArray(data)) {
        add_saved(data);
    }
}

function add_saved(items) {
    items.forEach(item => {
        const label = document.querySelector(`button[data-type="${item.type}"]`)?.dataset.label || "";
        const pts = item.points.map(p => ({
            x: parseInt(CANVAS_SIZE.w * p.x / 1e5),
            y: parseInt(CANVAS_SIZE.h * p.y / 1e5),
        }));
        const pos = {
            left: Math.min(...pts.map(p => p.x)),
            top: Math.min(...pts.map(p => p.y)),
        };
        poly_add(item.id, item.type, label, item.value, pts, pos, false);
    });
}

function render_text_icon(label) {
    return function (ctx, left, top, styleOverride, fabricObject) {
        const size = this.cornerSize || 24;
        ctx.save();
        ctx.translate(left, top);
        ctx.rotate(fabric.util.degreesToRadians(fabricObject.angle));
        ctx.font = `bold ${size * 0.7}px sans-serif`;
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillStyle = "#c00";
        ctx.fillText(label, 0, 0);
        ctx.restore();
    };
}

async function init_icons() {
    try {
        const urls = [
            "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.13.1/icons/x-circle-fill.svg",
            "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.13.1/icons/plus-circle.svg",
        ];
        const texts = await Promise.all(urls.map(u => fetch(u).then(r => r.text()).catch(() => null)));
        texts.forEach((svg, i) => {
            if (!svg) return;
            const img = document.createElement("img");
            img.src = "data:image/svg+xml," + encodeURIComponent(svg);
            ICONS[i === 0 ? "x-circle-fill" : "plus-circle"] = img;
        });
    } catch (e) {
        /* CDN bloklansa ham ROI ishlaydi */
    }
    showWorkspace();
    await load_saved();
}

function render_icon(imgOrLabel) {
    if (typeof imgOrLabel === "string") {
        return render_text_icon(imgOrLabel);
    }
    return function (ctx, left, top, styleOverride, fabricObject) {
        const size = this.cornerSize || 24;
        ctx.save();
        ctx.translate(left, top);
        ctx.rotate(fabric.util.degreesToRadians(fabricObject.angle));
        ctx.drawImage(imgOrLabel, -size / 2, -size / 2, size, size);
        ctx.restore();
    };
}

function update_polygon_fills() {
    const active = canvas.getActiveObject();
    const selected = new Set();
    if (active) {
        if (active.type === "polygon") selected.add(active);
        else if (active.type === "activeSelection") {
            active.getObjects().forEach(o => { if (o.type === "polygon") selected.add(o); });
        }
    }
    canvas.getObjects("polygon").forEach(poly => {
        const isSel = selected.has(poly);
        if (!isSel && poly._editing) poly._toggle_editing();
        poly.set("fill", isSel ? SELECTED_FILL : TRANSPARENT);
    });
    canvas.requestRenderAll();
}

function poly_add(id, type, label, value = "", points = null, pos = null, select = true) {
    points = points || [
        {x: 0, y: 0},
        {x: POLY_DEFAULT_SIZE, y: 0},
        {x: POLY_DEFAULT_SIZE, y: POLY_DEFAULT_SIZE},
        {x: 0, y: POLY_DEFAULT_SIZE},
    ];
    pos = pos || {
        left: CENTER.x - POLY_DEFAULT_SIZE / 2,
        top: CENTER.y - POLY_DEFAULT_SIZE / 2,
    };
    const poly = new fabric.Polygon(points, {
        left: pos.left,
        top: pos.top,
        fill: TRANSPARENT,
        strokeWidth: 3,
        stroke: "grey",
        objectCaching: false,
        transparentCorners: false,
        cornerColor: "blue",
    });
    poly._id = id || newRoiId();
    poly._editing = true;
    poly._type = type;
    poly._label = label;
    poly._value = value;
    poly._toggle_editing = function () {
        poly._editing = !poly._editing;
        if (poly._editing) {
            poly.cornerStyle = "circle";
            poly.cornerColor = "rgba(0,0,255,0.5)";
            poly.hasBorders = false;
            poly.controls = fabric.controlsUtils.createPolyControls(poly);
        } else {
            poly.cornerColor = "blue";
            poly.cornerStyle = "rect";
            poly.hasBorders = true;
            poly.controls = fabric.controlsUtils.createObjectDefaultControls();
            const delIcon = ICONS["x-circle-fill"];
            const addIcon = ICONS["plus-circle"];
            poly.controls.deleteControl = new fabric.Control({
                x: 0.5, y: -0.5, offsetY: -16, offsetX: 16,
                cursorStyle: "pointer",
                mouseUpHandler: delete_object,
                render: render_icon(delIcon || "×"),
                cornerSize: 24,
            });
            poly.controls.assignControl = new fabric.Control({
                x: 0.5, y: -0.5, offsetY: 16, offsetX: 16,
                cursorStyle: "pointer",
                mouseUpHandler: (e, t) => assign_modal?.show(),
                render: render_icon(addIcon || "+"),
                cornerSize: 24,
            });
        }
        poly.setCoords();
    };
    poly._toggle_editing();
    const superRender = poly._render.bind(poly);
    poly._render = function (ctx) {
        superRender(ctx);
        ctx.font = "24px Arial";
        ctx.fillStyle = "#000";
        ctx.textAlign = "center";
        ctx.fillText(this._value, 0, 0);
    };
    poly.on("mousedblclick", () => { poly._toggle_editing(); canvas.requestRenderAll(); });
    canvas.add(poly);
    if (select) canvas.setActiveObject(poly);
    return poly;
}

function delete_object(e, transform) {
    if (!confirm(gettext("Haqiqatda o'chirishni xohlaysizmi?"))) return;
    transform.target.canvas.remove(transform.target);
    transform.target.canvas.requestRenderAll();
}

function load_poly_data() {
    const out = [];
    canvas.getObjects("polygon").forEach(poly => {
        const matrix = poly.calcTransformMatrix();
        const pts = poly.points.map(p => {
            const pt = new fabric.Point(p.x - poly.pathOffset.x, p.y - poly.pathOffset.y);
            return fabric.util.transformPoint(pt, matrix);
        }).map(p => ({
            x: parseInt(1e5 * p.x / CANVAS_SIZE.w),
            y: parseInt(1e5 * p.y / CANVAS_SIZE.h),
        }));
        out.push({
            id: String(poly._id || newRoiId()),
            type: parseInt(poly._type, 10) || 0,
            value: String(poly._value ?? "").trim(),
            points: pts,
        });
    });
    return out;
}

if (canvas) {
    canvas.on("selection:created", update_polygon_fills);
    canvas.on("selection:updated", update_polygon_fills);
    canvas.on("selection:cleared", update_polygon_fills);
}

if (assign_modal_el) {
    assign_modal_el.addEventListener("show.bs.modal", () => {
        const obj = canvas?.getActiveObject();
        if (!obj) return;
        assign_modal_el.querySelector("form label").innerText = obj._label;
        assign_modal_el.querySelector(".modal-title").innerText = obj._label;
        assign_modal_el.querySelector("form input").value = obj._value;
    });
    assign_modal_el.querySelector("form")?.addEventListener("submit", e => {
        e.preventDefault();
        const obj = canvas.getActiveObject();
        if (obj) {
            obj._value = assign_modal_el.querySelector("form input").value;
            canvas.requestRenderAll();
        }
        assign_modal?.hide();
    });
}

document.querySelectorAll("#id_buttons button").forEach(btn => {
    btn.addEventListener("click", () => {
        if (!roiReady) {
            alert(gettext("Kamera rasmi hali yuklanmadi. «Rasmni edge dan yuklash» yoki biroz kuting."));
            return;
        }
        const poly = poly_add(undefined, parseInt(btn.dataset.type, 10), btn.dataset.label, defaultZoneName());
        if (poly && assign_modal) {
            canvas.setActiveObject(poly);
            assign_modal.show();
        }
    });
});

document.querySelector("#id_btn_save")?.addEventListener("click", () => {
    const payload = load_poly_data();
    for (const row of payload) {
        if (!row.points || row.points.length < 3) {
            alert(gettext("Har bir zona kamida 3 ta nuqtadan iborat bo'lishi kerak"));
            return;
        }
    }
    fetch(window.location.pathname, {
        method: "POST",
        headers: {"Content-Type": "application/json", ...csrf_header()},
        body: JSON.stringify(payload),
    })
        .then(async r => {
            const data = await r.json().catch(() => ({}));
            if (!r.ok) {
                alert(formatRoiErrors(data));
                return;
            }
            let msg = data.message || gettext("Saqlandi");
            if (data.edge_synced === false) {
                msg += "\n" + gettext("Edge serverga sinxronlash keyinroq uriniladi.");
            }
            alert(msg);
        })
        .catch(() => alert(gettext("Saqlashda xato")));
});

document.querySelector("#id_input_load_json")?.addEventListener("change", e => {
    roiJsonFiles = Array.from(e.target.files || []);
    alert(gettext("Yuklandi") + ": " + roiJsonFiles.length);
});

window.addEventListener("roi-frame-ready", () => init_icons());
setTimeout(() => { if (!roiReady) init_icons(); }, 8000);
