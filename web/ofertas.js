const $ = (id) => document.getElementById(id);
const marcadas = () => [...document.querySelectorAll('.card input:checked')]
                       .map(i => i.closest('.card'));

// Los iconos se dibujan, no se escriben: un ✓ o un 📤 de la fuente del sistema
// cambia de forma y de peso en cada maquina y no es del mismo trazo que el
// resto. Todos salen de aca, a 1.7 de grosor y con las puntas redondas.
const ICO = {
  check:  '<path d="M4.5 12.5l5 5 10-11"/>',
  baja:   '<path d="M12 4v11m0 0l-4.2-4.2M12 15l4.2-4.2"/>' +
          '<path d="M4.5 17v2.5a1 1 0 0 0 1 1h13a1 1 0 0 0 1-1V17"/>',
  envia:  '<path d="M4.5 12L20 4.5l-7 15.5-2.4-6.1z"/>',
  copia:  '<rect x=9 y=9 width=11 height=11 rx=2.5/>' +
          '<path d="M5 15.5V5.5a1.5 1.5 0 0 1 1.5-1.5H15"/>',
  fuera:  '<path d="M14.5 4H20v5.5"/><path d="M20 4l-8.5 8.5"/>' +
          '<path d="M18 14.5V19a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h4.5"/>',
  cierra: '<path d="M6.5 6.5l11 11M17.5 6.5l-11 11"/>',
  alerta: '<path d="M12 8.5v5"/><path d="M12 17v.01"/>' +
          '<path d="M12 3.5L2.8 19.5a1 1 0 0 0 .87 1.5h16.66a1 1 0 0 0 .87-1.5z"/>',
  editar: '<path d="M12 20h9"/><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/>',
};
const ico = (n, clase) =>
  `<svg class="ico ${clase || ''}" viewBox="0 0 24 24" fill=none stroke=currentColor
        stroke-width=1.7 stroke-linecap=round stroke-linejoin=round
        aria-hidden=true>${ICO[n]}</svg>`;

$('cerrar').innerHTML = ico('cierra');
$('editorCerrar').innerHTML = ico('cierra');
$('zipBtn').insertAdjacentHTML('afterbegin', ico('baja'));

function contar() {
  const n = marcadas().length;
  $('barra').hidden = !n && !$('lista').children.length;
  $('cuenta').textContent = n === 1 ? '1 subasta elegida'
                                    : `${n} subastas elegidas`;
  $('hacer').disabled = !n;
}
document.addEventListener('change', e => {
  if (e.target.matches('.card input')) contar();
});

$('limpiar').onclick = () => {
  document.querySelectorAll('.card input:checked').forEach(i => {
    i.checked = false;
    // El estado se va con la seleccion: una tarjeta en verde de una tanda
    // anterior mentiria sobre lo que se acaba de hacer.
    i.closest('.card').removeAttribute('data-est');
  });
  contar();
};

function estado(card, est, texto) {
  card.dataset.est = est;
  card.querySelector('.est').textContent = texto;
}

// ── El modal ──────────────────────────────────────────────────────────────
// Abrir y cerrar no tocan la lista: la tanda sigue corriendo con el modal
// cerrado y `Ver los carruseles` la devuelve tal cual estaba.
function abrir() {
  $('capa').hidden = false;
  document.body.style.overflow = 'hidden';
  $('cerrar').focus();
}
function cerrar() {
  $('capa').hidden = true;
  document.body.style.overflow = '';
  $('ver').hidden = !$('lista').children.length;
  contar();
}
$('cerrar').onclick = cerrar;
$('ver').onclick = abrir;
$('capa').onclick = e => { if (e.target === $('capa')) cerrar(); };
document.addEventListener('keydown', e => {
  if (e.key === 'Escape' && !$('capa').hidden) cerrar();
});

// ── Un bloque por subasta ─────────────────────────────────────────────────
function bloque(card) {
  const el = document.createElement('article');
  el.className = 'obra';
  el.dataset.fase = 'cola';
  el.dataset.id = card.dataset.id;
  el.innerHTML = `
    <header class=obra-cab>
      <label class=marca>
        <input type=checkbox disabled aria-label="Marcar para publicar">
        <span class=marca-caja>${ico('check')}</span>
      </label>
      <h3 class=obra-nom></h3>
      <code class=obra-slug></code>
      <span class=chip><i class=chip-punto></i><b class=chip-txt>En cola</b></span>
    </header>
    <div class=obra-cuerpo>
      <div class=obra-slides>
        <figure class=slide></figure><figure class=slide></figure>
        <figure class=slide></figure><figure class=slide></figure>
      </div>
      <div class=obra-copy>
        <span class=copy-tit>Copy</span>
        <div class=copy-hueso><i></i><i></i><i></i><i></i><i></i></div>
        <textarea class=copy-area spellcheck=false disabled
                  aria-label="Copy del carrusel"></textarea>
        <div class=copy-pie>
          <button class=pill-ghost type=button data-hace=copiar disabled>
            ${ico('copia')}Copiar</button>
          <button class=pill-publicar type=button data-hace=publicar disabled>
            ${ico('envia')}Publicar</button>
        </div>
        <p class=obra-dice role=status></p>
      </div>
    </div>`;
  el.querySelector('.obra-nom').textContent = card.dataset.nombre || card.dataset.id;
  // La foto de la subasta ocupa el primer hueco mientras se hace el carrusel:
  // tres bloques esperando se distinguen por el auto, no por el nombre.
  if (card.dataset.foto)
    el.querySelector('.slide').innerHTML =
      `<img src="${card.dataset.foto}" alt="" loading=lazy>`;
  $('lista').appendChild(el);
  return el;
}

// Lo que llega cuando `/lote` responde bien: los cuatro slides, el copy, y los
// controles que hasta ahora estaban apagados.
function llenar(el, j) {
  el.dataset.fase = 'listo';
  el.dataset.slug = j.slug;
  el._datosLote = j; // Guardar datos para edición posterior
  el.querySelector('.obra-slug').textContent = j.slug;
  el.querySelector('.chip-txt').textContent = 'Listo';
  
  pintarSlidesBloque(el, j);

  const ta = el.querySelector('.copy-area');
  ta.value = j.copy || '';
  ta.disabled = false;
  el.querySelectorAll('button[data-hace],.marca input')
    .forEach(b => { b.disabled = false; });

  // El copy se guarda solo, como en el estudio: el archivo es la fuente de
  // verdad y es lo que viaja en el ZIP.
  let guarda = null;
  ta.oninput = () => {
    clearTimeout(guarda);
    guarda = setTimeout(() => fetch('/copy', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ slug: j.slug, texto: ta.value }),
    }).catch(() => {}), 700);
  };

  el.querySelector('[data-hace=copiar]').onclick = async () => {
    await navigator.clipboard.writeText(ta.value);
    dice(el, 'ok', 'Copiado al portapapeles');
  };
  prepararPublicar(el);
  el.querySelector('.marca input').onchange = cuantasMarcadas;
  cuantasMarcadas();
}

function pintarSlidesBloque(el, j) {
  const slidesCont = el.querySelector('.obra-slides');
  slidesCont.innerHTML = (j.slides || []).map((u, n) => {
    const esCierre = n === (j.slides.length - 1);
    const overlay = esCierre ? '' : `<div class="slide-overlay">${ico('editar')}<span>Ajustar</span></div>`;
    // tabindex+role+aria-label solo en las editables: la placa de cierre no
    // reacciona a nada, marcarla como boton seria prometer una accion que no
    // existe.
    const foco = esCierre ? '' : `tabindex=0 role=button aria-label="Reencuadrar foto ${n + 1}"`;
    return `<figure class="slide" data-idx="${n}" ${foco}
      title="${esCierre ? 'Placa de cierre' : 'Clic para reencuadrar y ajustar'}">
      <img src="${u}" alt="Slide ${n + 1}" loading="lazy">
      ${overlay}
    </figure>`;
  }).join('');

  // Clic o teclado (Enter/Espacio) editan las fotos del auto (slides 0, 1, 2):
  // antes solo el mouse podia abrir el editor, y no habia forma de llegar ahi
  // navegando solo con teclado.
  slidesCont.querySelectorAll('.slide').forEach(fig => {
    const idx = parseInt(fig.dataset.idx, 10);
    if (idx < (j.slides.length - 1)) {
      fig.onclick = () => abrirEditorFoto(el, idx);
      fig.onkeydown = e => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          abrirEditorFoto(el, idx);
        }
      };
    }
  });
}

// Y lo que llega cuando se cae. El error del lote casi siempre es que la web
// no dio año o transmision, y eso se arregla en el estudio: el bloque lleva el
// camino, no solo la queja.
function fallar(el, mensaje) {
  el.dataset.fase = 'error';
  el.querySelector('.chip-txt').textContent = 'No salió';
  el.querySelector('.obra-cuerpo').innerHTML = `
    <div class=obra-error>
      ${ico('alerta', 'ico-lg')}
      <p class=error-dice></p>
      <a class=pill-ghost href="/estudio?oferta=${el.dataset.id}" target=_blank
         rel=noopener>${ico('fuera')}Abrirla en el estudio</a>
    </div>`;
  el.querySelector('.error-dice').textContent = mensaje;
}

function dice(el, clase, texto) {
  const p = el.querySelector('.obra-dice');
  p.textContent = texto;
  p.className = 'obra-dice ' + clase;
}

// ── Publicar ──────────────────────────────────────────────────────────────
// Dos toques, siempre: publicar manda el post al feed y eso no se deshace. El
// segundo toque tiene cuatro segundos; pasados, el boton vuelve solo.
function armar(btn, quieto, confirma, hace) {
  let reloj = null;
  btn.innerHTML = quieto;
  delete btn.dataset.armado;
  btn.onclick = () => {
    if (btn.dataset.armado) {
      clearTimeout(reloj);
      delete btn.dataset.armado;
      btn.innerHTML = quieto;
      return hace();
    }
    btn.dataset.armado = '1';
    btn.innerHTML = ico('alerta') + confirma;
    reloj = setTimeout(() => {
      delete btn.dataset.armado;
      btn.innerHTML = quieto;
    }, 4000);
  };
}

function prepararPublicar(el) {
  armar(el.querySelector('[data-hace=publicar]'),
        ico('envia') + 'Publicar', 'Confirmar', () => publicarUno(el));
}

async function publicarUno(el) {
  const btn = el.querySelector('[data-hace=publicar]');
  const ta = el.querySelector('.copy-area');
  btn.disabled = true;
  btn.innerHTML = '<i class=girito></i>Publicando…';
  dice(el, 'yendo', 'Subiendo al bucket y publicando…');
  try {
    const r = await fetch('/publicar', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ slug: el.dataset.slug, texto: ta.value }) });
    const j = await r.json();
    if (!j.ok) throw new Error(j.error || 'falló');
    el.dataset.fase = 'publicado';
    el.querySelector('.chip-txt').textContent =
      j.estado === 'publicado' ? 'Publicado' : 'Programado';
    btn.innerHTML = ico('check') + 'Publicado';
    btn.onclick = null;
    const marca = el.querySelector('.marca input');
    marca.checked = false; marca.disabled = true;
    dice(el, 'ok', j.estado === 'publicado' ? 'Está en el feed'
                                            : `Queda en la agenda: ${j.cuando}`);
    return true;
  } catch (err) {
    btn.disabled = false;
    armar(btn, ico('envia') + 'Reintentar', 'Confirmar', () => publicarUno(el));
    dice(el, 'mal', err.message);
    return false;
  } finally {
    cuantasMarcadas();
  }
}

const paraPublicar = () =>
  [...document.querySelectorAll('.obra[data-fase=listo] .marca input:checked')]
  .map(i => i.closest('.obra'));

// Mientras la fila corre, `cuantasMarcadas` no puede volver a encender el
// boton entre una publicacion y la siguiente: seria mandar la misma tanda dos
// veces.
let publicando = false;

function cuantasMarcadas() {
  const n = paraPublicar().length;
  const btn = $('pubTodas');
  btn.disabled = !n || publicando;
  armar(btn, ico('envia') + (n ? `Publicar ${n}` : 'Publicar'),
        n === 1 ? 'Confirmar: 1 al feed' : `Confirmar: ${n} al feed`,
        publicarMarcadas);
}

// Una detras de otra y no en paralelo: son subidas al bucket mas la API de
// Instagram, y si una falla hay que poder decir cual.
async function publicarMarcadas() {
  const cola = paraPublicar();
  publicando = true;
  $('pubTodas').disabled = true;
  try {
    for (const el of cola) {
      el.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
      await publicarUno(el);
    }
  } finally {
    publicando = false;
    cuantasMarcadas();
  }
}

// ── La tanda ──────────────────────────────────────────────────────────────
// Una oferta por peticion, dos peticiones en vuelo.
//
// Cada subasta tarda cerca de un minuto, y medido en esta maquina ese minuto es
// casi todo espera de red: el modelo que mira las ocho fotos son 35 s, el que
// escribe el copy unos 20 s, y el render son 7 s de CPU. En fila, esos 55 s de
// espera no hacen nada.
//
// Dos en vuelo los solapan y los renders se serializan solos: el servidor es un
// ThreadingHTTPServer y en Cloud Run `--concurrency 8` con 2 GiB aguanta dos
// Chromium (el pico medido de uno es 704 MiB). Cuatro no —ni de memoria ni de
// CPU—, y ademas cuatro tarjetas cambiando de estado a la vez no se leen. Dos
// es el numero que sale de la memoria del contenedor, no una preferencia.
const EN_VUELO = 2;

$('hacer').onclick = async () => {
  const cards = marcadas();
  if (!cards.length) return;
  $('hacer').disabled = true; $('limpiar').disabled = true;
  $('lista').innerHTML = '';
  $('cabAcciones').hidden = true;
  $('cabIcono').innerHTML = '<i class=anillo></i>';
  delete $('cabIcono').dataset.fin;
  $('pista').hidden = false;
  $('pistaFill').style.transform = 'scaleX(0)';
  $('cabTexto').textContent = 'Haciendo los carruseles…';
  $('cabCuenta').textContent = `0 de ${cards.length}`;
  abrir();

  // Todos los bloques primero, en el orden de la pantalla. Con dos en vuelo
  // terminan desordenadas, y crearlos al llegar dejaba la lista bailando.
  const bloques = cards.map(c => bloque(c));

  const hechos = [];
  let siguiente = 0, cerradas = 0;
  const trabajador = async () => {
    while (siguiente < cards.length) {
      const i = siguiente++;
      const card = cards[i], el = bloques[i];
      el.dataset.fase = 'haciendo';
      el.querySelector('.chip-txt').textContent = 'Haciendo el carrusel…';
      estado(card, 'haciendo', 'haciendo el carrusel…');
      try {
        const r = await fetch('/lote', {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ codigo: card.dataset.id,
                                 nombre: card.dataset.nombre }) });
        const j = await r.json();
        if (!j.ok) throw new Error(j.error || 'falló');
        llenar(el, j);
        hechos.push(j.slug);
        estado(card, 'listo', j.slug);
      } catch (err) {
        // Una que falla no detiene el lote: lo normal es que sea una
        // negociable sin precio base, y las otras nueve no tienen la culpa.
        fallar(el, err.message);
        estado(card, 'error', err.message);
      }
      // Cuantas cerraron, no cual va: con dos en vuelo "3 de 10" no señala nada.
      cerradas++;
      $('pistaFill').style.transform = `scaleX(${cerradas / cards.length})`;
      $('cabCuenta').textContent = `${cerradas} de ${cards.length}`;
      $('paso').textContent = `${cerradas} de ${cards.length}`;
    }
  };
  await Promise.all(Array.from({ length: Math.min(EN_VUELO, cards.length) },
                               trabajador));

  $('pista').hidden = true;
  $('cabIcono').innerHTML = ico(hechos.length ? 'check' : 'alerta', 'ico-lg');
  $('cabIcono').dataset.fin = hechos.length ? 'bien' : 'mal';
  $('cabTexto').textContent = hechos.length === cards.length
    ? (hechos.length === 1 ? 'El carrusel está listo'
                           : `Los ${hechos.length} carruseles están listos`)
    : (hechos.length ? `${hechos.length} de ${cards.length} salieron`
                     : 'Ninguno salió');
  $('cabCuenta').textContent = '';
  $('cabAcciones').hidden = false;
  $('zipBtn').hidden = !hechos.length;
  if (hechos.length)
    $('zipBtn').href = '/descargar-lote?slugs=' +
                       encodeURIComponent(hechos.join(','));
  $('paso').textContent = hechos.length
    ? `${hechos.length} de ${cards.length} listos` : 'ninguno salió';
  $('hacer').disabled = false; $('limpiar').disabled = false;
  cuantasMarcadas();
};

// ── Editor Rápido Flotante ────────────────────────────────────────────────
let editorActivo = null; // { el, idx, slug, foto, foco, escala, rawFoco }

function pctOf(s) {
  return (s || '50% 50%').split(' ').map(parseFloat);
}

function clamp(v) {
  return Math.min(100, Math.max(0, v));
}

function abrirEditorFoto(el, idx) {
  const j = el._datosLote;
  if (!j || !j.slug || !j.fotos || !j.fotos[idx]) return;
  
  const f = j.fotos[idx];
  let src = typeof f === 'string' ? f : f.src;
  // Si viene como autos/63173-xxx.jpeg convertir a /auto/xxx
  let imgUrl = src;
  if (imgUrl.startsWith('autos/')) {
    imgUrl = '/auto/' + imgUrl.replace('autos/', '');
  } else if (!imgUrl.startsWith('/') && !imgUrl.startsWith('http')) {
    imgUrl = '/' + imgUrl;
  }
  
  const foco = (typeof f === 'object' && f.foco) ? f.foco : '50% 50%';
  const escala = (typeof f === 'object' && f.escala) ? f.escala : 1.0;
  
  editorActivo = {
    el,
    idx,
    slug: j.slug,
    src: typeof f === 'string' ? f : f.src,
    imgUrl,
    foco,
    escala
  };

  $('editorTitulo').textContent = `Ajustar Foto ${idx + 1} · ${el.querySelector('.obra-nom').textContent}`;
  $('editorImg').src = imgUrl;
  $('editorZoom').value = escala;
  $('editorZoomOut').value = Number(escala).toFixed(2) + '×';
  $('editorMsg').textContent = '';
  $('editorMsg').className = 'editor-msg';
  $('editorGuardar').disabled = false;
  $('editorGuardar').innerHTML = ico('check') + 'Guardar y re-renderizar';

  actualizarVistaEditor();
  $('capaEditor').hidden = false;
}

function cerrarEditor() {
  $('capaEditor').hidden = true;
  editorActivo = null;
}

function actualizarVistaEditor() {
  if (!editorActivo) return;
  const img = $('editorImg');
  img.style.objectPosition = editorActivo.foco;
  if (editorActivo.escala === 1) {
    img.style.transform = '';
    img.style.transformOrigin = '';
  } else {
    img.style.transform = `scale(${editorActivo.escala})`;
    img.style.transformOrigin = editorActivo.foco;
  }
  $('editorZoom').value = editorActivo.escala;
  $('editorZoomOut').value = Number(editorActivo.escala).toFixed(2) + '×';
}

function travelEditor() {
  const frame = $('editorFrame');
  const img = $('editorImg');
  const side = frame.clientWidth || 380;
  const w = img.naturalWidth || 800;
  const h = img.naturalHeight || 600;
  if (!w || !h) return { x: 0, y: 0 };
  const cover = Math.max(side / w, side / h);
  const extra = side * ((editorActivo ? editorActivo.escala : 1) - 1);
  return { x: w * cover - side + extra, y: h * cover - side + extra };
}

function setFocusEditor(px, py) {
  if (!editorActivo) return;
  editorActivo.foco = clamp(px).toFixed(1) + '% ' + clamp(py).toFixed(1) + '%';
  actualizarVistaEditor();
}

// Drag & drop dentro del frame de edición
let dragEditor = null;
const editorFrame = $('editorFrame');

editorFrame.addEventListener('pointerdown', e => {
  if (!editorActivo) return;
  dragEditor = {
    x: e.clientX,
    y: e.clientY,
    foco: pctOf(editorActivo.foco),
    range: travelEditor()
  };
  editorFrame.setPointerCapture(e.pointerId);
  editorFrame.classList.add('dragging');
});

editorFrame.addEventListener('pointermove', e => {
  if (!dragEditor || !editorActivo) return;
  const dx = (e.clientX - dragEditor.x) / editorActivo.escala;
  const dy = (e.clientY - dragEditor.y) / editorActivo.escala;
  setFocusEditor(
    dragEditor.range.x ? dragEditor.foco[0] - (dx / dragEditor.range.x) * 100 : dragEditor.foco[0],
    dragEditor.range.y ? dragEditor.foco[1] - (dy / dragEditor.range.y) * 100 : dragEditor.foco[1]
  );
});

const releaseEditor = () => {
  dragEditor = null;
  editorFrame.classList.remove('dragging');
};
editorFrame.addEventListener('pointerup', releaseEditor);
editorFrame.addEventListener('pointercancel', releaseEditor);

editorFrame.addEventListener('wheel', e => {
  if (!editorActivo) return;
  e.preventDefault();
  editorActivo.escala = Math.min(3, Math.max(1, +(editorActivo.escala - e.deltaY * 0.0015).toFixed(3)));
  actualizarVistaEditor();
}, { passive: false });

editorFrame.addEventListener('keydown', e => {
  if (!editorActivo) return;
  const step = e.shiftKey ? 5 : 1;
  const [px, py] = pctOf(editorActivo.foco);
  const moves = { ArrowLeft: [-step, 0], ArrowRight: [step, 0], ArrowUp: [0, -step], ArrowDown: [0, step] };
  const m = moves[e.key];
  if (!m) return;
  e.preventDefault();
  setFocusEditor(px + m[0], py + m[1]);
});

$('editorZoom').oninput = () => {
  if (!editorActivo) return;
  editorActivo.escala = +$('editorZoom').value;
  actualizarVistaEditor();
};

$('editorRecenter').onclick = () => {
  if (!editorActivo) return;
  editorActivo.foco = '50% 50%';
  editorActivo.escala = 1.0;
  actualizarVistaEditor();
};

$('editorCerrar').onclick = cerrarEditor;
$('editorCancelar').onclick = cerrarEditor;
$('capaEditor').onclick = e => {
  if (e.target === $('capaEditor')) cerrarEditor();
};

document.addEventListener('keydown', e => {
  if (e.key === 'Escape' && !$('capaEditor').hidden) {
    cerrarEditor();
  }
});

$('editorGuardar').onclick = async () => {
  if (!editorActivo) return;
  const { el, idx, slug, foco, escala } = editorActivo;
  const btn = $('editorGuardar');
  const msg = $('editorMsg');
  
  btn.disabled = true;
  btn.innerHTML = '<i class="girito"></i>Guardando y renderizando…';
  msg.textContent = 'Renderizando slide con Remotion…';
  msg.className = 'editor-msg busy';
  
  try {
    const r = await fetch('/reencuadrar', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ slug, indice: idx, foco, escala })
    });
    const j = await r.json();
    if (!j.ok) throw new Error(j.error || 'No se pudo actualizar');
    
    // Actualizar datos locales del bloque y re-pintar sus slides
    el._datosLote.slides = j.slides;
    el._datosLote.fotos = j.fotos;
    pintarSlidesBloque(el, el._datosLote);
    
    dice(el, 'ok', `Foto ${idx + 1} actualizada`);
    cerrarEditor();
  } catch (err) {
    btn.disabled = false;
    btn.innerHTML = ico('alerta') + 'Reintentar guardar';
    msg.textContent = err.message;
    msg.className = 'editor-msg bad';
  }
};

contar();
