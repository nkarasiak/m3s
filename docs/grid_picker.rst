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
   .mp2{
     --b:var(--pst-color-border,#d0d7de);
     --s:var(--pst-color-surface,#f6f8fa);
     --bg:var(--pst-color-background,#fff);
     --t:var(--pst-color-text-base,#1f2328);
     --m:var(--pst-color-text-muted,#656d76);
     --p:var(--pst-color-primary,#0a7d91);
     --a:#1a7f37;
     font-size:.9rem;color:var(--t);margin:1.5rem 0;
   }
   .mp2 *{box-sizing:border-box;}
   .mp2-sec{margin:1.1rem 0;}
   .mp2-sec-hd{
     font-size:.7rem;font-weight:700;letter-spacing:.09em;
     text-transform:uppercase;color:var(--m);margin-bottom:.5rem;
   }
   /* Shape selector */
   .mp2-shapes{display:flex;flex-wrap:wrap;gap:.35rem;}
   .mp2-shape{
     display:flex;flex-direction:column;align-items:center;gap:.22rem;
     padding:.45rem .6rem;border:1.5px solid var(--b);border-radius:8px;
     background:var(--bg);cursor:pointer;min-width:68px;
     transition:border-color .14s,background .14s,transform .1s,color .14s;
     color:var(--t);font-family:inherit;
   }
   .mp2-shape:hover{border-color:var(--p);transform:translateY(-1px);}
   .mp2-shape.active{border-color:var(--p);background:rgba(10,125,145,.1);color:var(--p);}
   .mp2-shape svg{display:block;}
   .mp2-shape-lbl{font-size:.74rem;font-weight:600;white-space:nowrap;}
   /* Segmented 3-state controls */
   .mp2-props{display:flex;flex-direction:column;gap:.55rem;}
   .mp2-prop{display:flex;align-items:center;gap:.7rem;flex-wrap:wrap;}
   .mp2-prop-lbl{flex:0 0 155px;font-weight:600;font-size:.875rem;line-height:1.3;}
   .mp2-seg{display:flex;border:1px solid var(--b);border-radius:6px;overflow:hidden;}
   .mp2-seg button{
     padding:.3rem .65rem;border:none;border-right:1px solid var(--b);
     background:var(--bg);color:var(--t);cursor:pointer;font-size:.8rem;
     font-family:inherit;transition:background .12s,color .12s;white-space:nowrap;
   }
   .mp2-seg button:last-child{border-right:none;}
   .mp2-seg button:hover:not(.active):not(.nice):not(.req){background:var(--s);}
   .mp2-seg button.active{background:var(--s);color:var(--t);}
   .mp2-seg button.nice{background:rgba(10,125,145,.13);color:var(--p);font-weight:600;}
   .mp2-seg button.req{background:var(--p);color:#fff;font-weight:600;}
   /* Pill buttons */
   .mp2-pills{display:flex;flex-wrap:wrap;gap:.32rem;}
   .mp2-pill{
     padding:.26rem .7rem;border:1.5px solid var(--b);border-radius:999px;
     background:var(--bg);color:var(--t);cursor:pointer;font-size:.82rem;
     font-family:inherit;transition:border-color .13s,background .13s,color .13s;
   }
   .mp2-pill:hover:not(.active){border-color:var(--p);}
   .mp2-pill.active{
     border-color:var(--p);background:rgba(10,125,145,.1);
     color:var(--p);font-weight:600;
   }
   /* Toolbar */
   .mp2-toolbar{
     display:flex;align-items:center;justify-content:space-between;
     margin:1.1rem 0 .6rem;flex-wrap:wrap;gap:.4rem;
   }
   .mp2-count{font-size:.82rem;color:var(--m);}
   .mp2-reset{
     padding:.28rem .7rem;border:1px solid var(--b);border-radius:6px;
     background:transparent;color:var(--t);cursor:pointer;font-size:.82rem;font-family:inherit;
   }
   .mp2-reset:hover{background:var(--s);}
   /* Result cards */
   .mp2-cards{display:flex;flex-direction:column;gap:.65rem;}
   .mp2-card{
     border:1.5px solid var(--b);border-radius:10px;
     padding:.85rem 1.1rem;background:var(--bg);
     animation:mp2In .18s ease;
   }
   @keyframes mp2In{from{opacity:0;transform:translateY(5px);}to{opacity:1;transform:none;}}
   .mp2-card[data-rank="1"]{border-color:#b08300;}
   .mp2-card-hd{display:flex;align-items:center;justify-content:space-between;gap:.5rem;margin-bottom:.35rem;}
   .mp2-card-name{font-weight:700;font-size:.98rem;}
   .mp2-card-name a{text-decoration:none;color:inherit;}
   .mp2-card-name a:hover{color:var(--p);}
   .mp2-medal{font-size:1.1rem;flex-shrink:0;line-height:1;}
   .mp2-bar-wrap{height:3px;background:var(--s);border-radius:2px;margin-bottom:.4rem;}
   .mp2-bar-fill{height:100%;border-radius:2px;transition:width .3s ease;background:var(--p);}
   .mp2-card[data-rank="1"] .mp2-bar-fill{background:#b08300;}
   .mp2-card[data-rank="2"] .mp2-bar-fill{background:#848d97;}
   .mp2-card[data-rank="3"] .mp2-bar-fill{background:#bc4c00;}
   .mp2-tag{margin:0 0 .4rem;line-height:1.5;color:var(--t);}
   .mp2-chips{display:flex;flex-wrap:wrap;gap:.28rem;}
   .mp2-chip{
     font-size:.74rem;padding:.1rem .48rem;border-radius:999px;
     background:rgba(26,127,55,.1);color:var(--a);border:1px solid rgba(26,127,55,.22);
   }
   .mp2-empty{color:var(--m);font-style:italic;text-align:center;padding:1.5rem .5rem;}
   </style>

   <div class="mp2">

     <div class="mp2-sec">
       <div class="mp2-sec-hd">Cell shape</div>
       <div class="mp2-shapes" id="mp2-shapes">
         <button class="mp2-shape active" data-value="any">
           <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
             <circle cx="12" cy="12" r="8" stroke-dasharray="3 2"/>
           </svg>
           <span class="mp2-shape-lbl">Any</span>
         </button>
         <button class="mp2-shape" data-value="square">
           <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
             <rect x="4" y="4" width="16" height="16" rx="1"/>
           </svg>
           <span class="mp2-shape-lbl">Square</span>
         </button>
         <button class="mp2-shape" data-value="hexagon">
           <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
             <polygon points="12,3 21,7.5 21,16.5 12,21 3,16.5 3,7.5"/>
           </svg>
           <span class="mp2-shape-lbl">Hexagon</span>
         </button>
         <button class="mp2-shape" data-value="pentagon">
           <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
             <polygon points="12,3 20.6,9.2 17.3,19.3 6.7,19.3 3.4,9.2"/>
           </svg>
           <span class="mp2-shape-lbl">Pentagon</span>
         </button>
         <button class="mp2-shape" data-value="rectangle">
           <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
             <rect x="2" y="6" width="20" height="12" rx="1"/>
           </svg>
           <span class="mp2-shape-lbl">Rectangle</span>
         </button>
         <button class="mp2-shape" data-value="quadrilateral">
           <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
             <path d="M5,7 Q12,4 19,7 L19,17 Q12,20 5,17 Z"/>
           </svg>
           <span class="mp2-shape-lbl">Sph. quad</span>
         </button>
       </div>
     </div>

     <div class="mp2-sec">
       <div class="mp2-sec-hd">Properties needed</div>
       <div class="mp2-props">
         <div class="mp2-prop">
           <span class="mp2-prop-lbl">Equal-area cells</span>
           <div class="mp2-seg" data-field="equal">
             <button data-val="0" class="active">Don&#8217;t care</button>
             <button data-val="nice">Nice to have</button>
             <button data-val="req">Required</button>
           </div>
         </div>
         <div class="mp2-prop">
           <span class="mp2-prop-lbl">Exact nesting</span>
           <div class="mp2-seg" data-field="nest">
             <button data-val="0" class="active">Don&#8217;t care</button>
             <button data-val="nice">Nice to have</button>
             <button data-val="req">Required</button>
           </div>
         </div>
         <div class="mp2-prop">
           <span class="mp2-prop-lbl">Global &#177;90&#176;</span>
           <div class="mp2-seg" data-field="global">
             <button data-val="0" class="active">Don&#8217;t care</button>
             <button data-val="nice">Nice to have</button>
             <button data-val="req">Required</button>
           </div>
         </div>
         <div class="mp2-prop">
           <span class="mp2-prop-lbl">Km-labelled sizes</span>
           <div class="mp2-seg" data-field="km">
             <button data-val="0" class="active">Don&#8217;t care</button>
             <button data-val="nice">Nice to have</button>
             <button data-val="req">Required</button>
           </div>
         </div>
       </div>
     </div>

     <div class="mp2-sec">
       <div class="mp2-sec-hd">Precision needed</div>
       <div class="mp2-pills" data-field="prec">
         <button class="mp2-pill active" data-value="any">Any</button>
         <button class="mp2-pill" data-value="coarse">Coarse (100+ km)</button>
         <button class="mp2-pill" data-value="medium">Medium (km)</button>
         <button class="mp2-pill" data-value="fine">Fine (metres)</button>
       </div>
     </div>

     <div class="mp2-sec">
       <div class="mp2-sec-hd">Primary use case</div>
       <div class="mp2-pills" data-field="use">
         <button class="mp2-pill active" data-value="any">Any</button>
         <button class="mp2-pill" data-value="equalarea">Equal-area analytics</button>
         <button class="mp2-pill" data-value="hex">Hex aggregation</button>
         <button class="mp2-pill" data-value="database">Database indexing</button>
         <button class="mp2-pill" data-value="webmap">Web map tiles</button>
         <button class="mp2-pill" data-value="military">Military / surveying</button>
         <button class="mp2-pill" data-value="marine">Marine / fisheries</button>
         <button class="mp2-pill" data-value="address">Address replacement</button>
         <button class="mp2-pill" data-value="radio">Amateur radio</button>
         <button class="mp2-pill" data-value="global">Global / planetary</button>
       </div>
     </div>

     <div class="mp2-toolbar">
       <span class="mp2-count" id="mp2-count"></span>
       <button class="mp2-reset" id="mp2-reset">Reset all</button>
     </div>
     <div class="mp2-cards" id="mp2-cards"></div>
   </div>

   <script>
   (function () {
     var BASE = "auto_examples/grid_systems/plot_";
     var DOC = {
       eaquad:"eaquad",rhealpix:"rhealpix",a5:"a5",geohash:"geohash",h3:"h3",s2:"s2",
       mgrs:"mgrs",quadkey:"quadkey",slippy:"slippy",csquares:"csquares",
       gars:"gars",maidenhead:"maidenhead",pluscode:"pluscode"
     };
     var GRIDS = [
       {key:"eaquad",name:"EA-Quad",shape:"square",equal:"yes",nest:true,global:true,km:true,
        prec:["coarse","medium","fine"],uses:["equalarea","global"],
        tag:"Square, km-sized cells with identical ground area worldwide — fair counts and densities at any latitude."},
       {key:"rhealpix",name:"rHEALPix",shape:"square",equal:"yes",nest:true,global:true,km:false,
        prec:["coarse","medium","fine"],uses:["equalarea","global"],
        tag:"OGC-standardised equal-area DGGS (aperture 9) — exact nesting, square polar cells, scientific data cubes."},
       {key:"a5",name:"A5",shape:"pentagon",equal:"yes",nest:true,global:true,km:false,
        prec:["coarse","medium","fine"],uses:["equalarea","global"],
        tag:"Pentagonal equal-area DGGS on a dodecahedron, exact nesting, whole-world down to <30 mm²."},
       {key:"geohash",name:"Geohash",shape:"rectangle",equal:"no",nest:true,global:true,km:false,
        prec:["medium","fine"],uses:["database"],
        tag:"Fast prefix search; native support in Redis, MongoDB, Elasticsearch."},
       {key:"h3",name:"H3",shape:"hexagon",equal:"approx",nest:false,global:true,km:false,
        prec:["medium","fine"],uses:["hex","global"],
        tag:"Uniform hexagons, always 6 neighbours. Ride-sharing, logistics, data science."},
       {key:"s2",name:"S2",shape:"quadrilateral",equal:"approx",nest:true,global:true,km:false,
        prec:["coarse","medium","fine"],uses:["global"],
        tag:"Spherical quad-tree from global down to centimetre, no polar singularities."},
       {key:"mgrs",name:"MGRS",shape:"square",equal:"no",nest:false,global:false,km:true,
        prec:["coarse","fine"],uses:["military"],
        tag:"UTM-based NATO standard, 100 km down to 1 m."},
       {key:"quadkey",name:"Quadkey",shape:"square",equal:"no",nest:true,global:false,km:false,
        prec:["coarse","medium"],uses:["webmap"],
        tag:"Bing Maps tiles addressed by prefix string — aligned with web-map pipelines; cell area shrinks toward the poles."},
       {key:"slippy",name:"Slippy",shape:"square",equal:"no",nest:true,global:false,km:false,
        prec:["coarse","medium"],uses:["webmap"],
        tag:"OpenStreetMap tiles, universal z/x/y Web Mercator format."},
       {key:"csquares",name:"C-squares",shape:"rectangle",equal:"no",nest:true,global:true,km:false,
        prec:["coarse","medium"],uses:["marine"],
        tag:"International standard for oceanographic and marine biology data."},
       {key:"gars",name:"GARS",shape:"rectangle",equal:"no",nest:false,global:true,km:false,
        prec:["coarse"],uses:["military"],
        tag:"Global Area Reference System, coarse 30′ to 5′ area reference."},
       {key:"maidenhead",name:"Maidenhead",shape:"rectangle",equal:"no",nest:true,global:true,km:false,
        prec:["coarse","medium"],uses:["radio"],
        tag:"Ham-radio locator standard, optimised for voice QSO logging."},
       {key:"pluscode",name:"Plus Codes",shape:"rectangle",equal:"no",nest:true,global:true,km:false,
        prec:["medium","fine"],uses:["address"],
        tag:"Short, open codes that work anywhere, no street names needed."}
     ];
     var PREC_LABEL = {coarse:"Coarse (100+ km)",medium:"Medium (km)",fine:"Fine (metres)"};
     var USE_LABEL = {
       equalarea:"Equal-area analytics",hex:"Hex aggregation",database:"Database indexing",
       webmap:"Web map tiles",military:"Military / surveying",marine:"Marine / fisheries",
       address:"Address replacement",radio:"Amateur radio",global:"Global / planetary"
     };
     var SHAPE_LABEL = {
       square:"Square",hexagon:"Hexagon",pentagon:"Pentagon",
       rectangle:"Rectangle",quadrilateral:"Sph. quad"
     };
     var MEDALS = ["🥇","🥈","🥉"];

     function getShapes() {
       var vals = [];
       document.querySelectorAll("#mp2-shapes .mp2-shape.active").forEach(function (b) {
         if (b.dataset.value !== "any") vals.push(b.dataset.value);
       });
       return vals; // empty = any
     }
     function getSeg(field) {
       var a = document.querySelector(".mp2-seg[data-field=\"" + field + "\"] button.active");
       return a ? a.dataset.val : "0";
     }
     function getPills(field) {
       var a = document.querySelector(".mp2-pills[data-field=\"" + field + "\"] .mp2-pill.active");
       return a ? a.dataset.value : "any";
     }

     function score(g) {
       var s = 0, why = [];
       var shapes = getShapes();
       if (shapes.length > 0 && shapes.indexOf(g.shape) !== -1) { s += 3; why.push(SHAPE_LABEL[g.shape] + " cells"); }
       function prop(field, ok, label) {
         var m = getSeg(field);
         if (m === "req") { if (!ok) return false; s += 3; why.push(label); }
         else if (m === "nice" && ok) { s += 2; why.push(label); }
         return true;
       }
       if (!prop("equal", g.equal === "yes", "Equal-area")) return null;
       if (getSeg("equal") === "nice" && g.equal === "approx") { s += 1; why.push("Near equal-area"); }
       if (!prop("nest", g.nest, "Exact nesting")) return null;
       if (!prop("global", g.global, "Global ±90°")) return null;
       if (!prop("km", g.km, "Km-labelled")) return null;
       var prec = getPills("prec");
       if (prec !== "any" && g.prec.indexOf(prec) !== -1) { s += 2; why.push(PREC_LABEL[prec]); }
       var use = getPills("use");
       if (use !== "any" && g.uses.indexOf(use) !== -1) { s += 4; why.push(USE_LABEL[use]); }
       return { grid: g, score: s, why: why };
     }

     function anyFilter() {
       return getShapes().length > 0 || getPills("prec") !== "any" || getPills("use") !== "any" ||
         getSeg("equal") !== "0" || getSeg("nest") !== "0" ||
         getSeg("global") !== "0" || getSeg("km") !== "0";
     }

     function render() {
       var out = [];
       for (var i = 0; i < GRIDS.length; i++) {
         var r = score(GRIDS[i]);
         if (r) out.push(r);
       }
       out.sort(function (a, b) {
         return b.score !== a.score ? b.score - a.score : a.grid.name.localeCompare(b.grid.name);
       });
       var filtered = anyFilter();
       var show = filtered ? out.slice(0, 3) : out;
       var maxScore = (out.length && out[0].score > 0) ? out[0].score : 1;
       var count = document.getElementById("mp2-count");
       var box = document.getElementById("mp2-cards");
       if (out.length === 0) {
         count.textContent = "";
         box.innerHTML = "<div class=\"mp2-empty\">No grid satisfies every <strong>Required</strong> constraint. Relax one to see matches.</div>";
         return;
       }
       count.textContent = filtered
         ? out.length + " match" + (out.length !== 1 ? "es" : "") + " — top " + show.length + " shown"
         : "Set a preference above to rank " + out.length + " grid systems.";
       var html = "";
       for (var j = 0; j < show.length; j++) {
         var r = show[j];
         var url = BASE + DOC[r.grid.key] + ".html";
         var pct = Math.round(r.score / maxScore * 100);
         var chips = "";
         for (var k = 0; k < r.why.length; k++) {
           if (r.why[k]) chips += "<span class=\"mp2-chip\">" + r.why[k] + "</span>";
         }
         var rankAttr = filtered && j < 3 ? " data-rank=\"" + (j + 1) + "\"" : "";
         var medal = filtered && j < 3 ? "<span class=\"mp2-medal\">" + MEDALS[j] + "</span>" : "";
         html +=
           "<div class=\"mp2-card\"" + rankAttr + ">" +
             "<div class=\"mp2-card-hd\">" +
               "<span class=\"mp2-card-name\"><a href=\"" + url + "\">" + r.grid.name + "</a></span>" +
               medal +
             "</div>" +
             (filtered ? "<div class=\"mp2-bar-wrap\"><div class=\"mp2-bar-fill\" style=\"width:" + pct + "%\"></div></div>" : "") +
             "<p class=\"mp2-tag\">" + r.grid.tag + "</p>" +
             (chips ? "<div class=\"mp2-chips\">" + chips + "</div>" : "") +
           "</div>";
       }
       box.innerHTML = html;
     }

     document.getElementById("mp2-shapes").addEventListener("click", function (e) {
       var btn = e.target.closest(".mp2-shape");
       if (!btn) return;
       var anyBtn = document.querySelector("#mp2-shapes .mp2-shape[data-value=\"any\"]");
       if (btn.dataset.value === "any") {
         // Any clears all specific selections
         document.querySelectorAll("#mp2-shapes .mp2-shape").forEach(function (b) { b.classList.remove("active"); });
         anyBtn.classList.add("active");
       } else {
         // Toggle this shape; deactivate Any
         anyBtn.classList.remove("active");
         btn.classList.toggle("active");
         // If nothing selected, fall back to Any
         if (getShapes().length === 0) anyBtn.classList.add("active");
       }
       render();
     });

     document.querySelectorAll(".mp2-seg").forEach(function (seg) {
       seg.addEventListener("click", function (e) {
         var btn = e.target.closest("button");
         if (!btn) return;
         seg.querySelectorAll("button").forEach(function (b) { b.classList.remove("active", "nice", "req"); });
         var v = btn.dataset.val;
         btn.classList.add("active");
         if (v === "nice") btn.classList.add("nice");
         if (v === "req") btn.classList.add("req");
         render();
       });
     });

     document.querySelectorAll(".mp2-pills").forEach(function (pills) {
       pills.addEventListener("click", function (e) {
         var btn = e.target.closest(".mp2-pill");
         if (!btn) return;
         pills.querySelectorAll(".mp2-pill").forEach(function (b) { b.classList.remove("active"); });
         btn.classList.add("active");
         render();
       });
     });

     document.getElementById("mp2-reset").addEventListener("click", function () {
       document.querySelectorAll("#mp2-shapes .mp2-shape").forEach(function (b) { b.classList.remove("active"); });
       document.querySelector("#mp2-shapes .mp2-shape[data-value=\"any\"]").classList.add("active");
       document.querySelectorAll(".mp2-seg").forEach(function (seg) {
         seg.querySelectorAll("button").forEach(function (b) { b.classList.remove("active", "nice", "req"); });
         seg.querySelector("button[data-val=\"0\"]").classList.add("active");
       });
       document.querySelectorAll(".mp2-pills").forEach(function (pills) {
         pills.querySelectorAll(".mp2-pill").forEach(function (b) { b.classList.remove("active"); });
         pills.querySelector(".mp2-pill[data-value=\"any\"]").classList.add("active");
       });
       render();
     });

     render();
   })();
   </script>

Prefer a static reference? The :doc:`grid_comparison` page has the full feature
matrix, size tables, and per-property breakdowns.
