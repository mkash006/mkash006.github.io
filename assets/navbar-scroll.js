/* Navbar tint on scroll.
 *
 * The bar sits over the DNA banner in the banner's own navy, so the two read
 * as one block at the top of the page. As the banner scrolls past, the bar
 * fades to white and its type darkens to navy, which is the only way it stays
 * legible once the page background is behind it.
 *
 * The colours are interpolated from scroll position rather than switched at a
 * threshold, so the change tracks the scroll instead of snapping. They ride on
 * two custom properties the stylesheet reads (see theme.scss, "Navbar").
 */
(function () {
  "use strict";

  var DARK_BG = [18, 35, 54];      // #122336, sampled off the banner photo
  var LIGHT_BG = [255, 255, 255];
  var DARK_FG = "#fff";            // type over the banner
  var LIGHT_FG = "#2c3f51";        // navy once the bar has gone light
  var FLIP = 0.5;                  // where the type switches over
  var MAX_RUN = 170;               // px of scroll the fade spans, at most
  var FALLBACK_RUN = 170;          // when there is no banner to measure

  document.addEventListener("DOMContentLoaded", function () {
    var header = document.getElementById("quarto-header");
    if (!header) return;

    var run = FALLBACK_RUN;

    // Fade over exactly the strip of banner that passes behind the bar, so it
    // lands on white the moment the banner clears the top of the viewport.
    function measure() {
      var banner = document.querySelector(".quarto-title-banner");
      var height = banner ? banner.getBoundingClientRect().height : 0;
      var span = height ? height - header.offsetHeight : FALLBACK_RUN;
      run = Math.min(Math.max(span, 80), MAX_RUN);
    }

    function mix(a, b, t) {
      return "rgb(" +
        Math.round(a[0] + (b[0] - a[0]) * t) + "," +
        Math.round(a[1] + (b[1] - a[1]) * t) + "," +
        Math.round(a[2] + (b[2] - a[2]) * t) + ")";
    }

    function paint() {
      var t = Math.min(Math.max(window.scrollY / run, 0), 1);
      var light = t > FLIP;

      header.style.setProperty("--nav-bg", mix(DARK_BG, LIGHT_BG, t));
      // The background sweeps through mid-grey, where white type would wash
      // out, so the type flips at the crossover instead of fading with it and
      // carries a shadow until then.
      header.style.setProperty("--nav-fg", light ? LIGHT_FG : DARK_FG);
      header.style.setProperty("--nav-shadow", light
        ? "none"
        : "0 1px 3px rgba(10, 18, 28, " + (0.5 * (1 - t / FLIP) + 0.25) + ")");
      // Same crossover for the hamburger and the bar's own shadow.
      header.classList.toggle("is-light", light);
    }

    var queued = false;
    function onScroll() {
      if (queued) return;
      queued = true;
      requestAnimationFrame(function () {
        queued = false;
        paint();
      });
    }

    measure();
    paint();
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", function () {
      measure();
      paint();
    }, { passive: true });
  });
})();