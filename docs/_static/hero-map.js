// Hoist the first interactive (folium) map on a page to the very top of the
// article, just below the breadcrumb — so the explorer is the hero, above the
// title and prose — then size it to span the full viewport width. Sphinx-
// Gallery renders the docstring (title + "Go to the end" note) before any cell
// output, so the map can only be moved up client-side. Scoped to map output
// (.output_html containing an <iframe>); DataFrame HTML reprs are left in place.

// The hero (first interactive) map on the page, if any.
function m3sHeroMap() {
  var article = document.querySelector(".bd-article");
  if (!article) return null;
  var blocks = article.querySelectorAll(".output_html");
  for (var i = 0; i < blocks.length; i++) {
    if (blocks[i].querySelector("iframe")) return blocks[i];
  }
  return null;
}

// Size the hero map to the exact viewport width and align its left edge to the
// viewport's left edge. The CSS fallback (width:100vw centred on the article)
// overshoots by the scrollbar width because 100vw counts it; measuring the real
// rendered offset and correcting it in px sidesteps every vw/scrollbar/padding
// rounding issue, so the map lands pixel-flush at any width or zoom.
// Leaflet caches its pixel size, so widening the iframe element leaves the map
// painting at its old (narrow) size with empty bands on the sides. Folium names
// the map a `map_<hash>` global inside the iframe; call its invalidateSize() so
// it repaints to the new width and loads the newly exposed tiles.
function m3sInvalidateMap(iframe) {
  if (!iframe) return;
  var win;
  try { win = iframe.contentWindow; } catch (e) { return; }
  if (!win) return;
  for (var k in win) {
    if (k.indexOf("map_") !== 0) continue;
    try {
      var m = win[k];
      if (m && typeof m.invalidateSize === "function") m.invalidateSize();
    } catch (e) {}
  }
}

function m3sFitHeroMap() {
  var out = m3sHeroMap();
  if (!out) return;
  out.style.position = "relative";
  out.style.marginLeft = "0px";
  out.style.marginRight = "0px";
  out.style.left = "0px";
  out.style.width = document.documentElement.clientWidth + "px";
  // Distance from the viewport's left edge to the (now zero-margin) box.
  var offset = out.getBoundingClientRect().left;
  out.style.left = -offset + "px";
  m3sInvalidateMap(out.querySelector("iframe"));
}

function m3sInitHeroMap() {
  var out = m3sHeroMap();
  if (out) {
    // Hoist the map to the very top of the article, just below the breadcrumb,
    // so the explorer is the hero, above the title and prose.
    var article = document.querySelector(".bd-article");
    article.insertBefore(out, article.firstChild);
    // Re-fit once the iframe's Leaflet map has initialised, so invalidateSize
    // has a map to act on (the iframe document loads after this script runs).
    var iframe = out.querySelector("iframe");
    if (iframe) iframe.addEventListener("load", m3sFitHeroMap);
  }
  m3sFitHeroMap();
  // The folium map, web fonts and tiles settle after DOMContentLoaded; a
  // late-appearing vertical scrollbar shrinks the client width and would leave
  // the map a scrollbar-width too wide and off-centre, since the fit stores px.
  // Re-fit whenever the full-width container resizes (it tracks the client
  // width, unaffected by the map's own clipped overflow) and once after load.
  if (window.ResizeObserver) {
    var container = document.querySelector(".bd-container");
    if (container) new ResizeObserver(m3sFitHeroMap).observe(container);
  }
}

document.addEventListener("DOMContentLoaded", m3sInitHeroMap);
window.addEventListener("load", m3sFitHeroMap);
window.addEventListener("resize", m3sFitHeroMap);
