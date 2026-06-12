Grid Picker
===========

Answer a few questions about what you need and M3S ranks the grid systems that
fit best. Everything runs in your browser — nothing is sent anywhere.

.. tip::

   Leave a question on **Any** / **Don't care** to ignore it. Mark a property
   **Required** to exclude grids that lack it. The ranking and the *why* update
   live as you change answers.

.. raw:: html

   <style>
   .m3s-picker {
     --mp-border: var(--pst-color-border, #d0d7de);
     --mp-surface: var(--pst-color-surface, #f6f8fa);
     --mp-text: var(--pst-color-text-base, #1f2328);
     --mp-muted: var(--pst-color-text-muted, #656d76);
     --mp-primary: var(--pst-color-primary, #0a7d91);
     --mp-accent: var(--pst-color-success, #1a7f37);
     font-size: 0.95rem;
     margin: 1.5rem 0;
   }
   .m3s-picker * { box-sizing: border-box; }
   .m3s-picker .mp-grid {
     display: grid;
     grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
     gap: 0.9rem 1.2rem;
   }
   .m3s-picker .mp-field { display: flex; flex-direction: column; gap: 0.3rem; }
   .m3s-picker .mp-field label {
     font-weight: 600;
     color: var(--mp-text);
   }
   .m3s-picker select {
     padding: 0.45rem 0.6rem;
     border: 1px solid var(--mp-border);
     border-radius: 6px;
     background: var(--mp-surface);
     color: var(--mp-text);
     font-size: 0.92rem;
   }
   .m3s-picker .mp-actions {
     margin: 1.1rem 0 0.4rem;
     display: flex; gap: 0.6rem; align-items: center;
   }
   .m3s-picker button.mp-reset {
     padding: 0.4rem 0.9rem;
     border: 1px solid var(--mp-border);
     border-radius: 6px;
     background: transparent;
     color: var(--mp-text);
     cursor: pointer;
   }
   .m3s-picker button.mp-reset:hover { background: var(--mp-surface); }
   .m3s-picker .mp-results { margin-top: 1.3rem; display: flex; flex-direction: column; gap: 0.8rem; }
   .m3s-picker .mp-card {
     border: 1px solid var(--mp-border);
     border-left: 4px solid var(--mp-primary);
     border-radius: 8px;
     padding: 0.8rem 1rem;
     background: var(--mp-surface);
   }
   .m3s-picker .mp-card.mp-top { border-left-color: var(--mp-accent); }
   .m3s-picker .mp-card-head {
     display: flex; align-items: baseline; justify-content: space-between;
     gap: 0.6rem; flex-wrap: wrap;
   }
   .m3s-picker .mp-rank { font-size: 1.05rem; font-weight: 700; color: var(--mp-text); }
   .m3s-picker .mp-rank a { text-decoration: none; }
   .m3s-picker .mp-score { font-size: 0.8rem; color: var(--mp-muted); white-space: nowrap; }
   .m3s-picker .mp-tagline { margin: 0.25rem 0 0.5rem; color: var(--mp-text); }
   .m3s-picker .mp-chips { display: flex; flex-wrap: wrap; gap: 0.35rem; }
   .m3s-picker .mp-chip {
     font-size: 0.78rem;
     padding: 0.12rem 0.5rem;
     border-radius: 999px;
     background: rgba(26,127,55,0.12);
     color: var(--mp-accent);
     border: 1px solid rgba(26,127,55,0.25);
   }
   .m3s-picker .mp-empty { color: var(--mp-muted); font-style: italic; }
   </style>

   <div class="m3s-picker">
     <div class="mp-grid">
       <div class="mp-field">
         <label for="mp-shape">Cell shape</label>
         <select id="mp-shape">
           <option value="any">Any</option>
           <option value="square">Square</option>
           <option value="hexagon">Hexagon</option>
           <option value="pentagon">Pentagon</option>
           <option value="rectangle">Rectangle</option>
           <option value="quadrilateral">Spherical quadrilateral</option>
         </select>
       </div>
       <div class="mp-field">
         <label for="mp-equal">Equal-area cells</label>
         <select id="mp-equal">
           <option value="0">Don't care</option>
           <option value="nice">Nice to have</option>
           <option value="req">Required</option>
         </select>
       </div>
       <div class="mp-field">
         <label for="mp-nest">Exact hierarchical nesting</label>
         <select id="mp-nest">
           <option value="0">Don't care</option>
           <option value="nice">Nice to have</option>
           <option value="req">Required</option>
         </select>
       </div>
       <div class="mp-field">
         <label for="mp-global">Global coverage to &plusmn;90&deg;</label>
         <select id="mp-global">
           <option value="0">Don't care</option>
           <option value="nice">Nice to have</option>
           <option value="req">Required</option>
         </select>
       </div>
       <div class="mp-field">
         <label for="mp-km">Sizes labelled in kilometres</label>
         <select id="mp-km">
           <option value="0">Don't care</option>
           <option value="nice">Nice to have</option>
           <option value="req">Required</option>
         </select>
       </div>
       <div class="mp-field">
         <label for="mp-prec">Precision needed</label>
         <select id="mp-prec">
           <option value="any">Any</option>
           <option value="coarse">Coarse (100+ km)</option>
           <option value="medium">Medium (kilometres)</option>
           <option value="fine">Fine (metres)</option>
         </select>
       </div>
       <div class="mp-field">
         <label for="mp-use">Primary use case</label>
         <select id="mp-use">
           <option value="any">Any</option>
           <option value="equalarea">Equal-area analytics / rasterisation</option>
           <option value="hex">Hexagonal aggregation</option>
           <option value="database">Database indexing / proximity</option>
           <option value="webmap">Web map tiles</option>
           <option value="military">Military / surveying</option>
           <option value="marine">Marine / fisheries</option>
           <option value="address">Address replacement</option>
           <option value="radio">Amateur radio</option>
           <option value="global">Global / planetary scale</option>
         </select>
       </div>
     </div>

     <div class="mp-actions">
       <button type="button" class="mp-reset" id="mp-reset">Reset</button>
       <span class="mp-score" id="mp-count"></span>
     </div>

     <div class="mp-results" id="mp-results"></div>
   </div>

   <script>
   (function () {
     var BASE = "auto_examples/grid_systems/plot_";
     var DOC = {
       eaquad: "eaquad", rhealpix: "rhealpix", a5: "a5", geohash: "geohash", h3: "h3", s2: "s2",
       mgrs: "mgrs", quadkey: "quadkey", slippy: "slippy", csquares: "csquares",
       gars: "gars", maidenhead: "maidenhead", pluscode: "pluscode"
     };
     // equal: "yes" | "approx" | "no"; precision tags: coarse/medium/fine
     var GRIDS = [
       {key:"eaquad", name:"EA-Quad", shape:"square", equal:"yes", nest:true, global:true, km:true,
        prec:["coarse","medium","fine"], uses:["equalarea","global"],
        tag:"Square, km-sized cells with identical ground area worldwide — fair counts and densities at any latitude."},
       {key:"rhealpix", name:"rHEALPix", shape:"square", equal:"yes", nest:true, global:true, km:false,
        prec:["coarse","medium","fine"], uses:["equalarea","global"],
        tag:"OGC-standardised equal-area DGGS (aperture 9) — exact nesting, square polar cells, scientific data cubes."},
       {key:"a5", name:"A5", shape:"pentagon", equal:"yes", nest:true, global:true, km:false,
        prec:["coarse","medium","fine"], uses:["equalarea","global"],
        tag:"Pentagonal equal-area DGGS on a dodecahedron, exact nesting, whole-world down to <30 mm²."},
       {key:"geohash", name:"Geohash", shape:"rectangle", equal:"no", nest:true, global:true, km:false,
        prec:["medium","fine"], uses:["database"],
        tag:"Fast prefix search; native support in Redis, MongoDB, Elasticsearch."},
       {key:"h3", name:"H3", shape:"hexagon", equal:"approx", nest:false, global:true, km:false,
        prec:["medium","fine"], uses:["hex","global"],
        tag:"Uniform hexagons, always 6 neighbours. Ride-sharing, logistics, data science."},
       {key:"s2", name:"S2", shape:"quadrilateral", equal:"approx", nest:true, global:true, km:false,
        prec:["coarse","medium","fine"], uses:["global"],
        tag:"Spherical quad-tree from global down to centimetre, no polar singularities."},
       {key:"mgrs", name:"MGRS", shape:"square", equal:"no", nest:false, global:false, km:true,
        prec:["coarse","fine"], uses:["military"],
        tag:"UTM-based NATO standard, 100 km down to 1 m."},
       {key:"quadkey", name:"Quadkey", shape:"square", equal:"no", nest:true, global:false, km:false,
        prec:["coarse","medium"], uses:["webmap"],
        tag:"Bing Maps tiles addressed by prefix string — aligned with web-map pipelines; cell area shrinks toward the poles."},
       {key:"slippy", name:"Slippy", shape:"square", equal:"no", nest:true, global:false, km:false,
        prec:["coarse","medium"], uses:["webmap"],
        tag:"OpenStreetMap tiles, universal z/x/y Web Mercator format."},
       {key:"csquares", name:"C-squares", shape:"rectangle", equal:"no", nest:true, global:true, km:false,
        prec:["coarse","medium"], uses:["marine"],
        tag:"International standard for oceanographic and marine biology data."},
       {key:"gars", name:"GARS", shape:"rectangle", equal:"no", nest:false, global:true, km:false,
        prec:["coarse"], uses:["military"],
        tag:"Global Area Reference System, coarse 30' to 5' area reference."},
       {key:"maidenhead", name:"Maidenhead", shape:"rectangle", equal:"no", nest:true, global:true, km:false,
        prec:["coarse","medium"], uses:["radio"],
        tag:"Ham-radio locator standard, optimised for voice QSO logging."},
       {key:"pluscode", name:"Plus Codes", shape:"rectangle", equal:"no", nest:true, global:true, km:false,
        prec:["medium","fine"], uses:["address"],
        tag:"Short, open codes that work anywhere, no street names needed."}
     ];

     var SHAPE_LABEL = {square:"Square", hexagon:"Hexagon", pentagon:"Pentagon",
                        rectangle:"Rectangle", quadrilateral:"Spherical quad"};
     var PREC_LABEL = {coarse:"Coarse (100+ km)", medium:"Medium (km)", fine:"Fine (metres)"};
     var USE_LABEL = {equalarea:"Equal-area analytics", hex:"Hex aggregation",
                      database:"Database indexing", webmap:"Web map tiles",
                      military:"Military / surveying", marine:"Marine / fisheries",
                      address:"Address replacement", radio:"Amateur radio",
                      global:"Global / planetary"};

     function val(id) { return document.getElementById(id).value; }

     function score(g) {
       var s = 0, why = [];
       // Shape (soft)
       var shape = val("mp-shape");
       if (shape !== "any" && g.shape === shape) { s += 3; why.push(SHAPE_LABEL[shape] + " cells"); }

       // Three-state properties: equal, nest, global, km
       function prop(id, ok, strong, niceLabel) {
         var m = val(id);
         if (m === "req") {
           if (!ok) return false;          // disqualify
           s += 3; why.push(niceLabel);
         } else if (m === "nice") {
           if (ok) { s += strong ? 2 : 1; why.push(niceLabel); }
         }
         return true;
       }
       if (!prop("mp-equal", g.equal === "yes", g.equal === "yes",
                 g.equal === "yes" ? "Equal-area" : "")) return null;
       // approx equal-area: partial credit when "nice", never satisfies "required"
       if (val("mp-equal") === "nice" && g.equal === "approx") { s += 1; why.push("Near equal-area"); }
       if (!prop("mp-nest", g.nest, true, "Exact nesting")) return null;
       if (!prop("mp-global", g.global, true, "Global ±90°")) return null;
       if (!prop("mp-km", g.km, true, "Km-labelled")) return null;

       // Precision (soft)
       var prec = val("mp-prec");
       if (prec !== "any") {
         if (g.prec.indexOf(prec) !== -1) { s += 2; why.push(PREC_LABEL[prec]); }
       }
       // Use case (soft, strong signal)
       var use = val("mp-use");
       if (use !== "any") {
         if (g.uses.indexOf(use) !== -1) { s += 4; why.push(USE_LABEL[use]); }
       }
       return { grid: g, score: s, why: why };
     }

     function render() {
       var out = [];
       for (var i = 0; i < GRIDS.length; i++) {
         var r = score(GRIDS[i]);
         if (r) out.push(r);
       }
       out.sort(function (a, b) {
         if (b.score !== a.score) return b.score - a.score;
         return a.grid.name.localeCompare(b.grid.name);
       });

       var anyFilter = val("mp-shape") !== "any" || val("mp-prec") !== "any" ||
         val("mp-use") !== "any" || val("mp-equal") !== "0" || val("mp-nest") !== "0" ||
         val("mp-global") !== "0" || val("mp-km") !== "0";

       var top = anyFilter ? out.slice(0, 3) : out;
       var box = document.getElementById("mp-results");
       var count = document.getElementById("mp-count");

       if (out.length === 0) {
         box.innerHTML = '<p class="mp-empty">No grid satisfies every <strong>Required</strong> property. Relax one constraint to see matches.</p>';
         count.textContent = "";
         return;
       }

       count.textContent = anyFilter
         ? (out.length + " grid" + (out.length === 1 ? "" : "s") + " match — top " + top.length + " shown")
         : "Set a preference above to rank the " + out.length + " grids.";

       var html = "";
       for (var j = 0; j < top.length; j++) {
         var r = top[j];
         var url = BASE + DOC[r.grid.key] + ".html";
         var chips = "";
         for (var k = 0; k < r.why.length; k++) {
           if (r.why[k]) chips += '<span class="mp-chip">' + r.why[k] + '</span>';
         }
         html +=
           '<div class="mp-card' + (anyFilter && j === 0 ? ' mp-top' : '') + '">' +
             '<div class="mp-card-head">' +
               '<span class="mp-rank">' + (anyFilter ? (j + 1) + ". " : "") +
                 '<a href="' + url + '">' + r.grid.name + '</a></span>' +
               (anyFilter ? '<span class="mp-score">match score ' + r.score + '</span>' : '') +
             '</div>' +
             '<p class="mp-tagline">' + r.grid.tag + '</p>' +
             (chips ? '<div class="mp-chips">' + chips + '</div>' : '') +
           '</div>';
       }
       box.innerHTML = html;
     }

     var ids = ["mp-shape","mp-equal","mp-nest","mp-global","mp-km","mp-prec","mp-use"];
     ids.forEach(function (id) {
       document.getElementById(id).addEventListener("change", render);
     });
     document.getElementById("mp-reset").addEventListener("click", function () {
       document.getElementById("mp-shape").value = "any";
       document.getElementById("mp-prec").value = "any";
       document.getElementById("mp-use").value = "any";
       ["mp-equal","mp-nest","mp-global","mp-km"].forEach(function (id) {
         document.getElementById(id).value = "0";
       });
       render();
     });
     render();
   })();
   </script>

Prefer a static reference? The :doc:`grid_comparison` page has the full feature
matrix, size tables, and per-property breakdowns.
