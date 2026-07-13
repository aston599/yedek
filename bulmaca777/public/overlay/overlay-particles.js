/**

 * Arka plan parçacıkları — bulanık uçan yapboz, şekiller, baloncuklar.

 */

(function () {

  const params = new URLSearchParams(location.search);

  const MOTION_OFF = params.get("motion") === "0" || params.get("fx") === "0";



  const PUZZLE_PATH =

    "M4 2h5l1.5 2.5L12 2h6v5l2.5 2.5L18 12v6h-5l-2.5 1.5L12 22H6v-5L3.5 14.5 6 12V6L3.5 3.5 4 2z";



  const COLORS = ["#5ee0ff", "#7c5cff", "#ff6b6b", "#ffd54a", "#2ecc71", "#ff9f43", "#ffffff"];



  function puzzleSvg(color) {

    return `<svg viewBox="0 0 22 20" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">

      <path fill="${color}" d="${PUZZLE_PATH}" opacity="0.92"/>

    </svg>`;

  }



  function chatSvg(color) {

    return `<svg viewBox="0 0 24 20" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">

      <path fill="${color}" d="M4 2h16a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H9l-4 4v-4H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2z" opacity="0.85"/>

    </svg>`;

  }



  function rand(min, max) {

    return min + Math.random() * (max - min);

  }



  function pick(arr) {

    return arr[Math.floor(Math.random() * arr.length)];

  }



  function createParticle(i) {

    const kinds = ["puzzle", "puzzle", "puzzle", "dot", "dot", "tri", "sq", "plus", "chat", "cross"];

    const kind = pick(kinds);

    const el = document.createElement("span");

    const drift = `fx-drift-${(i % 5) + 1}`;

    const size =

      kind === "puzzle" ? rand(36, 72) : kind === "chat" ? rand(28, 48) : rand(10, 28);

    const blur = kind === "dot" ? rand(2, 8) : kind === "puzzle" ? rand(0, 4) : rand(1, 6);

    const color = pick(COLORS);



    el.className = `fx-particle fx-particle--${kind} ${drift}`;

    el.style.setProperty("--x", `${rand(0, 96)}%`);

    el.style.setProperty("--y", `${rand(0, 94)}%`);

    el.style.setProperty("--size", `${size}px`);

    el.style.setProperty("--blur", `${blur}px`);

    el.style.setProperty("--dur", `${rand(10, 26)}s`);

    el.style.setProperty("--delay", `${rand(-30, 0)}s`);

    el.style.setProperty("--op", `${rand(0.38, 0.78).toFixed(2)}`);

    el.style.setProperty("--rot", `${rand(0, 360)}deg`);



    el.style.setProperty("--pcolor", color);

    if (kind === "puzzle") el.innerHTML = puzzleSvg(color);

    else if (kind === "chat") el.innerHTML = chatSvg(color);



    return el;

  }



  function spawn(host) {

    host.replaceChildren();

    const urlCount = params.get("particles");

    const count = Number(urlCount) || Number(host.dataset.count) || 50;

    const frag = document.createDocumentFragment();

    for (let i = 0; i < count; i++) frag.appendChild(createParticle(i));

    host.appendChild(frag);

    host.dataset.ready = "1";

  }



  function init() {

    if (MOTION_OFF) return;

    const host = document.getElementById("fxParticles");

    if (!host) return;

    spawn(host);

  }



  function refresh() {

    if (MOTION_OFF) return;

    const host = document.getElementById("fxParticles");

    if (!host) return;

    spawn(host);

  }



  if (document.readyState === "loading") {

    document.addEventListener("DOMContentLoaded", init);

  } else {

    init();

  }



  window.BulmacaParticles = { init, refresh };

})();


