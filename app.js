(function(){
"use strict";
var SITES=window.SITES, ORDER=window.ORDER, GROUPS=window.GROUPS;
var MON={jan:"Jan",feb:"Feb",mar:"Mar",apr:"Apr",may:"May",jun:"Jun",jul:"Jul",aug:"Aug",sep:"Sep",oct:"Oct",nov:"Nov",dec:"Dec"};
var MNUM={jan:1,feb:2,mar:3,apr:4,may:5,jun:6,jul:7,aug:8,sep:9,oct:10,nov:11,dec:12};
var SENS={
  nisar:{name:"NISAR L-band radar",short:"NISAR",col:"#4cc9f0",rec:"NASA false colour: R = HH, G = HV, B = HH − HV (dB)",
    note:"L-band radar (provisional data). Sees through cloud and deeper into vegetation. Dark = water-like or smooth."},
  s1:{name:"Sentinel-1 C-band radar",short:"Sentinel-1",col:"#f4a259",rec:"Same colour logic: R = VV, G = VH, B = VV − VH (dB)",
    note:"C-band radar. Sees through cloud, reflects more off the canopy top. Not comparable dB for dB with NISAR."},
  s2:{name:"Sentinel-2 optical",short:"Sentinel-2",col:"#c3a6ff",rec:"True colour (natural colour photograph)",
    note:"Optical image. Easy to read, but stops at cloud and haze."}
};
function fmt(t){return (+t.slice(3))+" "+MON[t.slice(0,3)];}
function iso(t){return "2026-"+("0"+MNUM[t.slice(0,3)]).slice(-2)+"-"+("0"+(+t.slice(3))).slice(-2);}
function dnum(s){var p=s.split("-");return Date.UTC(+p[0],+p[1]-1,+p[2])/864e5;}
function fmtIso(s){var p=s.split("-");var m=["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"][+p[1]-1];return (+p[2])+" "+m;}
function esc(s){return String(s).replace(/[&<>"]/g,function(c){return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c];});}
function $(s,el){return (el||document).querySelector(s);}
function $$(s,el){return Array.prototype.slice.call((el||document).querySelectorAll(s));}
var CTX={};
var NEWS={as:'https://reliefweb.int/disaster/ff-2026-000139-ind',th:'https://www.theguardian.com/world/2026/oct/03/bangkok-thailand-floods-breaking-point-stagnant-lakes',dv:'https://www.latimes.com/world-nation/story/2026-08-26/at-least-22-killed-hundreds-missing-after-flash-floods-in-nepal',mt:'https://adaderana.lk/news/cmsllrmzm0002356pqtua97bp',pt:'https://www.joc.com/article/colombo-expands-box-capacity-as-regional-hub-competition-intensifies-6167847'};
function imgUrl(site,kind,tag){return "img/"+site.id+"_"+kind+"_"+tag+".webp";}
function chgUrl(site,file){return "img/"+site.id+"_change_"+file+".webp";}
function nearest(tags,isoDate){var d=dnum(isoDate),best=tags[0],bd=1e9;tags.forEach(function(t){var x=Math.abs(dnum(iso(t))-d);if(x<bd){bd=x;best=t;}});return best;}
var app=$("#app");
var timer=null, S=null, st=null;


/* ---------------- WHY THIS MATTERS (home, interactive) ---------------- */
var ROLES=[
 {k:"resp",n:"Disaster responders",g:"A first look at where water spread and when, even under storm cloud.",
  e:["#/site/th","Thailand","Open water in the study box rose from under 1% in early September to 17% on 30 September."],
  u:"Decide where to send a field team, or which official flood data to ask for first.",
  c:"Not a flood warning. Dark is consistent with water, not proof of it."},
 {k:"water",n:"Water and irrigation managers",g:"An independent check on reservoirs and irrigated land, beside the storage records you already have.",
  e:["#/site/sn","Senanayake Samudraya","The water-like share of the June outline fell from about 36% to about 25% by September."],
  u:"Compare the direction of change with storage records, and ask where the water went.",
  c:"Radar gives area, not water level or volume."},
 {k:"plan",n:"Planners and officials",g:"Where and when the ground changed, so you know where to ask for a ground check.",
  e:["#/site/mt","Matara","About 2.3 km² of land turned newly dark on 18 October, after the wettest three days of the season."],
  u:"Request gauge data or a site visit for these places before planning.",
  c:"Radar shows surface change, not always its cause."},
 {k:"farm",n:"Farmers and communities",g:"A picture of which fields and low ground stayed wet, or changed, through the season.",
  e:["#/site/mn","Minneriya","The dark area in the irrigated field zone fell from about 7.7 to 0.6 km² (preliminary)."],
  u:"Take the before/after slider to local officials as a concrete question.",
  c:"Water hidden under plants may not look dark, so the real flooded area can be larger."},
 {k:"sci",n:"Scientists and teachers",g:"A checked set of NISAR examples with dates, methods and limits, and a plain guide to reading radar.",
  e:["#/moisture","Rain test","The radar's green signal follows rain at three Sri Lankan places (r = 0.6 to 0.8)."],
  u:"Repeat the method with our public code, or teach radar with the guide.",
  c:"Provisional data and few dates: a clear link, not a measurement."}
];
function whyBlock(){
  return '<section class="sec" id="why"><h2 data-eb="01 · Impact">What do you get from this?</h2>'+
  '<p class="sub">In one line: radar shows what changed on the ground, and when, even through cloud, so you know where to look first. Pick who you are.</p>'+
  '<div class="roles" role="group" aria-label="Choose a role">'+ROLES.map(function(r,i){return '<button type="button" data-role="'+r.k+'" aria-pressed="'+(i===0)+'">'+r.n+'</button>';}).join("")+'</div>'+
  '<div class="rolebox" id="rolebox" aria-live="polite"></div></section>';
}
function drawRole(k){
  var r=ROLES.filter(function(x){return x.k===k;})[0]||ROLES[0];
  $("#rolebox").innerHTML=
   '<div class="rrow"><span class="rlab">You get</span><p>'+esc(r.g)+'</p></div>'+
   '<div class="rrow"><span class="rlab">Seen in our data</span><p><a href="'+r.e[0]+'"><b>'+esc(r.e[1])+':</b> '+esc(r.e[2])+' →</a></p></div>'+
   '<div class="rrow"><span class="rlab">You could</span><p>'+esc(r.u)+'</p></div>'+
   '<p class="rc"><b>Limit:</b> '+esc(r.c)+'</p>';
  $$("[data-role]").forEach(function(b){b.setAttribute("aria-pressed",b.dataset.role===r.k?"true":"false");});
}

/* ---------------- HOME ---------------- */
function renderHome(){
  stopPlay(); document.body.classList.remove("site-open");
  var cards='<div class="cards flat">';
  GROUPS.forEach(function(g){
    g[1].forEach(function(id){
      var s=SITES[id];
      var cx=CTX[s.id], im=cx?cx.src:imgUrl(s,"nisar",s.defaults.nisar[1]), alt=cx?cx.alt:("NISAR radar image of "+s.short), lab=cx?cx.tag:"NISAR radar view";
      cards+='<a class="card" href="#/site/'+s.id+'"><div class="cimg"><img src="'+im+'" alt="'+esc(alt)+'" ><span class="clab">'+esc(lab)+'</span></div><div class="ctag"><b>'+esc(s.country)+'</b> · '+esc(s.group)+'</div><div class="sname">'+esc(s.short)+'</div><q>'+esc(s.question)+'</q><span class="go">Open the story →</span></a>';
    });
  });
  cards+='</div>';
  app.innerHTML=
  '<section class="hero" id="top"><video autoplay muted loop playsinline poster="media/poster.jpg" aria-hidden="true"><source src="media/loop.mp4" type="video/mp4"></video>'+
  '<div class="hero-in"><h1>Dancing<br>with the <span>SARs</span></h1>'+
  '<p class="lead">Radar from the NASA-ISRO NISAR satellite watches Earth\'s surface change, day or night and through cloud. Seven places, four countries, June to November 2026, through wet and dry spells.</p>'+
  '<a class="cta" href="#stories">Explore the stories</a>'+
  '<small>Looping video: real NISAR images of Matara (Sri Lanka) and the Assam floodplain. Provisional data, shown with sensor and date.</small></div></section>'+
  whyBlock()+
  '<section class="sec"><h2 data-eb="02 · The basics">What you are looking at</h2><p class="sub">Radar is an active sensor: it sends its own microwave pulses and listens for the echo.</p><div class="three">'+
  '<div class="box"><h3>Radar sees through cloud</h3><p>That is why it can show floods that optical satellites cannot see in the rainy season.</p></div>'+
  '<div class="box"><h3>Water is dark, land is not</h3><p>Smooth water reflects the pulse away from the satellite, so it looks dark. Vegetation and buildings scatter it back.</p></div>'+
  '<div class="box"><h3>Two radars and an optical camera</h3><p>NISAR (L-band) is paired with Sentinel-1 (C-band radar) and Sentinel-2 (optical), so you can see what each one adds.</p></div>'+
  '</div><p class="cap" style="margin-top:14px">New to radar? <a href="#/radar">Read the plain-words guide</a>.</p></section>'+
  '<section class="sec" id="stories"><h2 data-eb="03 · The stories">Stories</h2><p class="sub">Pick a question. Each story has a before/after slider, a time-lapse, a time series with rain, and a three-sensor view.</p>'+cards+'</section>'+
  '<section class="sec" id="validate"><h2 data-eb="04 · The test">Does the colour mean something?</h2><p class="sub">The stories above read radar colours as water, ground and plants. This test checks that claim against rainfall, in three places.</p>'+
  '<div class="nwhomes"><a class="nwhome" href="#/moisture"><div class="nwh-img"><img src="img/nw_a_20260924.webp" alt="Green pixels only in a NISAR image of Nawalapitiya after heavy rain"></div>'+
  '<div class="nwh-txt"><div class="ctag"><b>Sri Lanka</b> · Validation test · wet hill country</div><div class="sname">Nawalapitiya: can radar feel the rain?</div>'+
  '<q>Does the radar’s green signal rise and fall with the weekly rain, on morning and evening passes, in forest and in open land?</q>'+
  '<p class="nwh-s">19 passes · rain in the week before each one · time-lapse and graph</p><span class="go">Open the test →</span></div></a>'+
  '<a class="nwhome" href="#/moisture/ampara"><div class="nwh-img"><img src="img/am_d_20261020.webp" alt="Green pixels only in a NISAR evening-pass image of Ampara after heavy rain"></div>'+
  '<div class="nwh-txt"><div class="ctag"><b>Sri Lanka</b> · Validation test · dry-zone east</div><div class="sname">Ampara: does it work in the dry zone too?</div>'+
  '<q>Does the same signal follow the rain, and independent satellite soil moisture, in the drier east?</q>'+
  '<p class="nwh-s">19 passes · rain and soil moisture · a harder test, with a weaker result</p><span class="go">Open the test →</span></div></a>'+
  '<a class="nwhome" href="#/moisture/ratnapura"><div class="nwh-img"><img src="img/rn_a_20260924.webp" alt="Green pixels only in a NISAR morning-pass image of Ratnapura after heavy rain"></div>'+
  '<div class="nwh-txt"><div class="ctag"><b>Sri Lanka</b> · Validation test · south-west wet zone</div><div class="sname">Ratnapura: a third place</div>'+
  '<q>Does the green signal follow the rain again, on both passes, in a third area?</q>'+
  '<p class="nwh-s">20 passes · rain and soil moisture · same method</p><span class="go">Open the test →</span></div></a></div></section>'+
  '<section class="sec" id="colours"><h2 data-eb="05 · Reading colours">How to read the colours</h2><p class="sub">All NISAR images use the same fixed recipe, so colours mean the same thing everywhere.</p><div class="legend">'+
  '<div class="leg"><div class="sw" style="background:#b9e03e"></div><div><b>Green to yellow</b><br>vegetation, forest</div></div>'+
  '<div class="leg"><div class="sw" style="background:linear-gradient(135deg,#4a2fe8,#8a54d8)"></div><div><b>Blue to purple</b><br>smooth or bare ground</div></div>'+
  '<div class="leg"><div class="sw" style="background:linear-gradient(135deg,#03040a 50%,#2a14c8 50%)"></div><div><b>Black or deep blue-violet</b><br>very smooth: water, calm sea, radar shadow</div></div>'+
  '<div class="leg"><div class="sw" style="background:#f2bde8"></div><div><b>Pink to white</b><br>buildings, flooded vegetation</div></div></div>'+
  '<div class="recipe">NISAR: red = HH, green = HV, blue = HH − HV in dB (NASA SVS 5661 recipe). Sentinel-1 uses the same recipe with VV and VH. The stretch is fixed per site, so colours compare across dates. Colours are a display; numbers come from the charts. L-band and C-band are never compared dB for dB.</div><p style="margin:18px 0 0"><a class="btn" href="#/polar" style="text-decoration:none">Which polarizations highlight these changes? HH vs HV →</a></p></section>'+
  '<section class="sec" id="next"><h2 data-eb="06 · Looking ahead">What next for NISAR</h2><p class="sub">Drawn from what we saw in these seven stories. Each step is a possibility, not a finished service. Click a step to open it.</p><div class="steps">'+
  '<details class="step"><summary onclick="var o=!this.parentNode.open;var d=this.parentNode.parentNode.children;for(var i=0;i<d.length;i++)d[i].open=o;return false;"><span class="sn">1 · Now</span><h3>What radar already shows</h3></summary><ul><li><b>Through cloud:</b> Thailand and Assam show water when optical images are blocked.</li><li><b>Reservoirs and hazards:</b> Senanayake, Minneriya and Devighat change in ways radar can see.</li></ul></details>'+
  '<details class="step"><summary onclick="var o=!this.parentNode.open;var d=this.parentNode.parentNode.children;for(var i=0;i<d.length;i++)d[i].open=o;return false;"><span class="sn">2 · With validated data</span><h3>What gets sharper</h3></summary><ul><li><b>Flood extents:</b> validated products could give them within days.</li><li><b>Rain check:</b> repeat our Rain test to tell wetting of the ground from real change.</li></ul></details>'+
  '<details class="step"><summary onclick="var o=!this.parentNode.open;var d=this.parentNode.parentNode.children;for(var i=0;i<d.length;i++)d[i].open=o;return false;"><span class="sn">3 · With ground data</span><h3>What becomes measured</h3></summary><ul><li><b>Accuracy:</b> gauges and field surveys would turn "consistent with" into a measured score.</li><li><b>Official flood extents:</b> would let us check how well radar matches them.</li></ul></details>'+
  '</div></section>'+footer();
  drawRole("resp"); $$("[data-role]").forEach(function(b){b.onclick=function(){drawRole(b.dataset.role);};});
  window.scrollTo(0,0);
}
function footer(){
  return '<footer id="about"><div class="in ftc"><p class="ftl"><b>Team SkySense</b> · NASA Space Apps Challenge, Colombo 2026 · Dancing with the SARs<br>Anuththara Divyanjalie · Muditha Kumara · Mayumi Maleesha</p>'+
  '<details class="ftd"><summary>Data sources and AI disclosure</summary>'+
  '<p>NISAR L2 GCOV, provisional release (CRID P05023) and, in the Nawalapitiya rain test, validated release (CRID P05036), NASA-ISRO, via ASF DAAC. Data searched and downloaded with ASF Data Search (Vertex) and NASA Earthdata. False-colour recipe: NASA Scientific Visualization Studio, SVS 5661.</p>'+
  '<p>Contains modified Copernicus Sentinel data (2026). Sentinel-1 via OPERA RTC-S1 (ASF DAAC); Sentinel-2 L2A via Copernicus / ESA and AWS Earth Search.</p>'+
  '<p>Rain: NASA POWER (MERRA-2 model, about 50 km, not a rain gauge). Rainfall exploration: NASA GES DISC Giovanni (Earthdata). Rain test: NASA GPM IMERG Late daily (GPM_3IMERGDL v07) at Nawalapitiya and Ratnapura and IMERG Early daily (GPM_3IMERGDE v07) at Ampara; AMSR2 soil moisture (LPRM, 6.9 GHz) via Giovanni at Ampara and Ratnapura; forest mask: ESA WorldCover 2021 v200 (CC BY 4.0). Site context checks: Google Earth Pro.</p>'+
  '<p>Analysis scripts, this web app and the drafting of text were assisted by Claude (Anthropic).</p></details></div></footer>';
}


/* ---------------- KEY TAKEAWAY (plain language) ---------------- */
var TK={
 th:{one:"Radar saw open water in the Prachin Buri study area jump from under 1% to about 17% of the land after the wettest spell of the season, and it was still about 14% on 12 October.",
  pol:"Radar sees through cloud, so how far the water spread, and how long dark areas lingered, can be followed even on overcast days. Comparing dates could help officials see which areas stay wet longest and plan drainage, pumping and relief.",
  pub:"Fields and villages that stay dark on the maps for weeks are places where water is lingering. Residents and community groups can use the slider to ask local officials where water is slow to leave.",
  care:"This is not a flood warning. Water hidden under plants may not look dark, so the real flooded area is probably larger."},
 as:{one:"Radar showed about 45 km² of the Assam floodplain study area turn dark (water-like) on 22 July after 240 mm of rain in 12 days. The darkening was still large in early August and had faded by late August and October. This fits the reported flood, which began on 19 July and peaked on 27–28 July.",
  pol:"A free, all-weather record of how long a floodplain stays wet helps with timing relief, restoring farmland and understanding where the river spreads. Comparing seasons could support planning of embankments and land use.",
  pub:"Farmers and river-side communities can see where the water spread and when land dried out again, in a way that cloudy skies do not hide.",
  care:"Dates and impacts come from ReliefWeb (IFRC, 6 Aug 2026), not our own field check. Rain here is a coarse 50 km model value."},
 dv:{one:"After the 26 August flood, radar shows a lasting change along the Trishuli river: a wider, sediment-covered channel and stripped banks, still visible in October.",
  pol:"A before and after map of where the river corridor changed can inform hazard zoning, rebuilding, and the safety of roads and hydropower sites, and can be repeated after each monsoon.",
  pub:"People living near the river can see how far its path changed near their homes. This helps start local conversations about safe building and escape routes.",
  care:"This shows surface change, not flooding depth, and it is not a hazard map. Ordinary monsoon rain does not explain it, but radar alone cannot say the exact cause."},
 mt:{one:"On 18 October about 2.3 km² of land around Matara became newly dark (water-like or saturated) after the wettest three days of the season. Optical satellites could not see the ground because of cloud, but radar could.",
  pol:"Radar can give flood evidence when it is cloudy, which supports situation awareness for disaster response, irrigation and paddy management. Pairing it with rain and river gauges could sharpen early decisions.",
  pub:"Farmers and floodplain residents can see which fields turned wet or ponded. It can support asking for drainage or help for those areas.",
  care:"Radar cannot separate natural flooding from flooded paddy, and no field check has confirmed it. It is not a warning service."},
 pt:{one:"Terminal areas at Colombo Port change between almost every satellite pass (about 28 to 44% of pixels), while a nearby city block stays at about 1%.",
  pol:"Port and logistics planners get a free, all-weather way to watch how land is used and how busy yards are, without needing access to the site. Over years it could show growth and reclamation.",
  pub:"Anyone can see where the port is changing day to day compared with the surrounding city. It is useful context for discussing coastal development.",
  care:"Radar cannot separate containers from ships and cannot count containers or measure throughput. The port is always active, so this is not an event."},
 mn:{one:"Around Minneriya, the dark (watery) area in the irrigated field zone fell from 11.6 km² on 20 June to about 0.1 km² from 19 August. This is consistent with the end of the Yala irrigation season. The tank zone does not follow reservoir storage.",
  pol:"Irrigation and agriculture officers could follow how water is being used across a season, field by field, and compare it with the cropping calendar to check water management.",
  pub:"Farmers and tank-users can see that water in the fields changes through the season, which supports talking about water sharing.",
  care:"Radar alone cannot tell flooded fields from ploughed ones. The Mahaweli plan's dates are proposals, not records, and tank-zone area is not a storage measure."},
 sn:{one:"Open water inside the June outline of Senanayake Samudraya fell by about a quarter or more by September and had not recovered by mid-October. The Irrigation Department's storage series fell over the same ten dates (r = 0.84), from 28.4% to 16.3% of active storage.",
  pol:"Water managers get an independent, all-weather check on how much surface a reservoir covers, which can support drought planning and decisions on releases for irrigation.",
  pub:"Downstream farmers and communities can see a sign that the reservoir was lower than in June and may want to ask what the official water levels are.",
  care:"Radar shows the direction of surface area only, not level, volume or capacity. Agreement with storage is over ten dates that share a downward trend. The size of the change depends on how the frame edge is trimmed, and rain here is a coarse model value."}
};
function tkHTML(id){
  var t=TK[id]; if(!t)return "";
  return '<section class="tk"><div class="tkin"><div class="tkh"><span>Key takeaway</span><h2>'+esc(t.one)+'</h2></div>'+
   '<div class="tkgrid"><div><h3>For policy makers and officials</h3><p>'+esc(t.pol)+'</p></div>'+
   '<div><h3>For residents, farmers and communities</h3><p>'+esc(t.pub)+'</p></div>'+
   '<div class="care"><h3>Handle with care</h3><p>'+esc(t.care)+'</p></div></div></div></section>';
}

var BBOX={am:[81.45,81.70,7.10,7.35],th:[101.38,101.46,14.00,14.08],as:[94.15,94.45,26.80,26.98],dv:[85.114,85.154,27.868,27.908],mt:[80.45,80.75,5.90,6.10],mn:[80.82,81.02,7.95,8.10],sn:[81.38,81.62,7.15,7.42],pt:[79.8232,79.8504,6.9243,6.9513],nw:[80.45,80.62,6.90,7.10],rn:[80.28,80.55,6.60,6.80]};
function mapInfo(id){
  var b=BBOX[id]; if(!b)return null;
  var lat=(b[2]+b[3])/2, lon=(b[0]+b[1])/2;
  var span=Math.max(b[1]-b[0],(b[3]-b[2]));
  var z=Math.max(8,Math.min(15,Math.round(Math.log(360/span)/Math.LN2)-1));
  var c=lat.toFixed(5)+","+lon.toFixed(5);
  return {lat:lat,lon:lon,z:z,c:c,
    open:"https://www.google.com/maps/search/?api=1&query="+c,
    sat:"https://www.google.com/maps/@"+c+","+z+"z/data=!3m1!1e3",
    embed:"https://maps.google.com/maps?q="+c+"&z="+z+"&t=k&output=embed"};
}
function mapBtn(id){var m=mapInfo(id);if(!m)return "";return '<div class="locbtns lt"><a class="btn" target="_blank" rel="noopener" href="'+m.open+'">📍 See this place on Google Maps</a><a class="btn" target="_blank" rel="noopener" href="'+m.sat+'">🛰 Satellite view</a>'+(NEWS[id]?'<a class="btn" target="_blank" rel="noopener" href="'+NEWS[id]+'">📰 Related report ↗</a>':'')+'</div>';}
function checkHTML(c){
  if(!c)return "";
  return '<h3 class="chkh">'+esc(c.title)+'</h3><div class="chkw"><table class="chk"><tr>'+c.head.map(function(h){return "<th>"+esc(h)+"</th>";}).join("")+"</tr>"+
   c.rows.map(function(x){return "<tr>"+x.map(function(v){return "<td>"+esc(v)+"</td>";}).join("")+"</tr>";}).join("")+"</table></div><p class=\"chkn\">"+esc(c.note)+"</p>";
}
function tabsHTML(id){
  var t=TK[id], mi=mapInfo(id);
  var tabs=[], i;
  if(t){tabs.push(["tk","Key takeaway",
    '<h2 class="tkone">'+esc(t.one)+'</h2><div class="tkgrid"><div><h3>For policy makers and officials</h3><p>'+esc(t.pol)+'</p></div>'+
    '<div><h3>For residents, farmers and communities</h3><p>'+esc(t.pub)+'</p></div>'+
    '<div class="care"><h3>Handle with care</h3><p>'+esc(t.care)+'</p></div></div>']);}
  tabs.push(["see","What we see","<ul>"+S.see.map(function(x){return "<li>"+esc(x)+"</li>";}).join("")+"</ul>"+checkHTML(S.check)]);
  tabs.push(["data","Data used","<table>"+S.data.map(function(x){return "<tr><td>"+esc(x[0])+"</td><td>"+esc(x[1])+"</td></tr>";}).join("")+"</table>"]);
  tabs.push(["lim","Limits","<ul>"+S.limits.map(function(x){return "<li>"+esc(x)+"</li>";}).join("")+"</ul>"]);
  tabs.push(["why","Why it may happen",'<p class="whyp">'+esc(S.why)+'</p>']);
  if(mi){tabs.push(["loc","Where is this?",locBody(id)]);}
  return tabsShell(tabs,!!t);
}
function locBody(id){
  var mi=mapInfo(id), b=BBOX[id];
  return '<p class="locp">Centre of the study box: <b>'+mi.lat.toFixed(4)+'°N, '+mi.lon.toFixed(4)+'°E</b>. Box edges: '+b[0]+'–'+b[1]+'°E, '+b[2]+'–'+b[3]+'°N.</p>'+
    '<div class="locbtns"><a class="btn" target="_blank" rel="noopener" href="'+mi.open+'">📍 Open in Google Maps</a><a class="btn" target="_blank" rel="noopener" href="'+mi.sat+'">🛰 Satellite view</a></div>'+
    '<div class="locmap" id="locmap" data-src="'+mi.embed+'"><button class="btn" id="locload">Show the map here (needs internet)</button></div>';
}
function tabsShell(tabs,tk){
  var bar='<div class="tabbar" role="tablist" aria-label="Story details">'+tabs.map(function(x,k){return '<button role="tab" id="tab-'+x[0]+'" data-tab="'+x[0]+'" aria-selected="'+(k===0)+'" aria-controls="tp-'+x[0]+'">'+x[1]+'</button>';}).join("")+'</div>';
  var panes=tabs.map(function(x,k){return '<div class="tabpane" role="tabpanel" id="tp-'+x[0]+'" aria-labelledby="tab-'+x[0]+'"'+(k===0?"":" hidden")+'>'+x[2]+'</div>';}).join("");
  return '<section class="tabs'+(tk?' tk':'')+'"><div class="tkin">'+bar+panes+'</div></section>';
}
function wireTabs(){
  var tb=$$(".tabbar [data-tab]");
  function sel(k){
    tb.forEach(function(b){var on=b.dataset.tab===k;b.setAttribute("aria-selected",on);var p=document.getElementById("tp-"+b.dataset.tab);if(p)p.hidden=!on;});
  }
  tb.forEach(function(b,i){
    b.onclick=function(){sel(b.dataset.tab);};
    b.onkeydown=function(e){var j=-1;if(e.key==="ArrowRight")j=(i+1)%tb.length;if(e.key==="ArrowLeft")j=(i+tb.length-1)%tb.length;if(j>=0){tb[j].focus();sel(tb[j].dataset.tab);e.preventDefault();}};
  });
  var ll=$("#locload"); if(ll)ll.onclick=function(){var m=$("#locmap");m.innerHTML='<iframe title="Google Map of the study area"  referrerpolicy="no-referrer-when-downgrade" allowfullscreen src="'+m.dataset.src+'"></iframe>';};
}

/* ---------------- INTERACTIVE ADD-ONS ---------------- */
var SLOUT=[[80.25,9.83],[80.45,9.62],[80.40,9.54],[80.55,9.38],[80.81,9.27],[81.0,8.93],[81.23,8.57],[81.38,8.2],[81.70,7.72],[81.82,7.42],[81.83,6.87],[81.78,6.75],[81.65,6.5],[81.40,6.35],[81.30,6.2],[81.12,6.12],[80.80,6.02],[80.59,5.92],[80.22,6.03],[79.98,6.42],[79.96,6.58],[79.84,6.93],[79.83,7.2],[79.80,7.58],[79.83,8.03],[79.70,8.2],[79.85,8.6],[79.95,8.8],[80.05,9.1],[80.10,9.5],[80.05,9.7],[79.95,9.78]];
var PINS=[
 {id:"th",lon:101.42,lat:14.04,reg:1},{id:"as",lon:94.30,lat:26.89,reg:1},{id:"dv",lon:85.134,lat:27.888,reg:1},
 {id:"mt",lon:80.60,lat:6.00,sl:1},{id:"mn",lon:80.92,lat:8.025,sl:1},{id:"sn",lon:81.50,lat:7.285,sl:1},{id:"pt",lon:79.838,lat:6.938,sl:1},
 {id:"nw",lon:80.535,lat:7.0,sl:1,link:"#/moisture",name:"Nawalapitiya rain test",sub:"Sri Lanka · Validation test"}];
var mapSel="th";
function pinSVG(p,x,y,lab,dx,anchor,dy){dy=dy||0;
  return '<g class="pin'+(p.id===mapSel?' on':'')+'" data-pin="'+p.id+'" tabindex="0" role="button" aria-label="'+esc(lab)+'" transform="translate('+x.toFixed(1)+','+y.toFixed(1)+')"><circle class="halo" r="14"/><circle class="dot" r="6.5"/><text x="'+dx+'" y="'+(4+dy)+'" text-anchor="'+anchor+'">'+esc(lab)+'</text></g>';
}
function mapHTML(){
  var rs=22, rw=(104-74)*rs, rh=(31-3)*rs;
  function rx(l){return (l-74)*rs;} function ry(l){return (31-l)*rs;}
  var g="";
  for(var lo=75;lo<=104;lo+=5)g+='<line class="gr" x1="'+rx(lo)+'" y1="0" x2="'+rx(lo)+'" y2="'+rh+'"/><text class="gt" x="'+(rx(lo)+3)+'" y="'+(rh-5)+'">'+lo+'°E</text>';
  for(var la=5;la<=30;la+=5)g+='<line class="gr" x1="0" y1="'+ry(la)+'" x2="'+rw+'" y2="'+ry(la)+'"/><text class="gt" x="4" y="'+(ry(la)-4)+'">'+la+'°N</text>';
  var slbox='<rect class="slbox" x="'+rx(79.2)+'" y="'+ry(10.1)+'" width="'+((82.2-79.2)*rs)+'" height="'+((10.1-5.7)*rs)+'" rx="4"/>';
  var pins="";
  PINS.filter(function(p){return p.reg;}).forEach(function(p){var s=SITES[p.id];pins+=pinSVG(p,rx(p.lon),ry(p.lat),s.short,-12,"end");});
  var slh=4.3*0+ (10.1-5.7), ss=118, sw=(82.2-79.2)*ss, sh=slh*ss;
  function sx(l){return (l-79.2)*ss;} function sy(l){return (10.1-l)*ss;}
  var poly=SLOUT.map(function(c){return sx(c[0]).toFixed(1)+","+sy(c[1]).toFixed(1);}).join(" ");
  var spins="";
  var lab={mt:["Matara area",14,"start"],mn:["Minneriya",14,"start"],sn:["Senanayake Samudraya",-12,"end"],pt:["Colombo Port",-8,"start",24],nw:["Nawalapitiya",14,"start"]};
  PINS.filter(function(p){return p.sl;}).forEach(function(p){var L=lab[p.id];spins+=pinSVG(p,sx(p.lon),sy(p.lat),L[0],L[1],L[2],L[3]);});
  return '<div class="mapwrap"><figure class="mapfig"><svg viewBox="0 0 '+rw+' '+rh+'" class="mapsvg" role="img" aria-label="Locator map of the story sites in South Asia and Southeast Asia"><rect class="mbg" width="'+rw+'" height="'+rh+'" rx="12"/>'+g+slbox+
    '<text class="slt" x="'+rx(82.5)+'" y="'+(ry(8.2))+'">Sri Lanka ↘</text>'+pins+'</svg><figcaption>Locator grid (latitude and longitude), not a coastline map.</figcaption></figure>'+
   '<figure class="mapfig sl"><svg viewBox="0 0 '+sw.toFixed(0)+' '+sh.toFixed(0)+'" class="mapsvg" role="img" aria-label="Simplified outline of Sri Lanka with five study sites"><rect class="mbg" width="'+sw.toFixed(0)+'" height="'+sh.toFixed(0)+'" rx="12"/><polygon class="isl" points="'+poly+'"/>'+spins+'</svg><figcaption>Sri Lanka, simplified outline (not survey accuracy).</figcaption></figure></div>'+
   '<div class="mappre" id="mappre"></div>';
}
function pinInfo(id){
  var p=PINS.filter(function(x){return x.id===id;})[0];
  if(id==="nw"){return {title:"Nawalapitiya: can radar feel the rain?",tag:"Sri Lanka · Validation test",img:"img/nw_a_20260924.webp",big:"r = 0.73",small:"green radar signal vs the previous week’s rain (morning pass)",href:"#/moisture",gm:"https://www.google.com/maps/search/?api=1&query=7.00000,80.53500"};}
  var s=SITES[id], mi=mapInfo(id), cx=CTX[id];
  return {title:s.title,tag:s.country+" · "+s.group,img:cx?cx.src:imgUrl(s,"nisar",s.defaults.nisar[1]),big:s.stats[0][0],small:s.stats[0][1],href:"#/site/"+id,gm:mi.open};
}
function drawMapPre(){
  var i=pinInfo(mapSel), b=$("#mappre"); if(!b)return;
  b.innerHTML='<img src="'+i.img+'" alt=""><div class="mpt"><div class="ctag">'+esc(i.tag)+'</div><div class="sname">'+esc(i.title)+'</div><div class="mpbig">'+esc(i.big)+'</div><div class="mpsm">'+esc(i.small)+'</div>'+
   '<div class="locbtns"><a class="btn go" href="'+i.href+'" style="text-decoration:none">Open the story →</a><a class="btn" target="_blank" rel="noopener" href="'+i.gm+'" style="text-decoration:none">📍 Google Maps</a></div></div>';
}
function wireMap(){
  function sel(id){mapSel=id;$$(".pin").forEach(function(g){g.classList.toggle("on",g.dataset.pin===id);});drawMapPre();}
  $$(".pin").forEach(function(g){g.onclick=function(){sel(g.dataset.pin);};g.onkeydown=function(e){if(e.key==="Enter"||e.key===" "){sel(g.dataset.pin);e.preventDefault();}};});
  drawMapPre();
}
function countUp(el){
  var txt=el.textContent, re=/\d+(?:\.\d+)?/g, parts=[], m, last=0;
  while((m=re.exec(txt))){parts.push({pre:txt.slice(last,m.index),v:parseFloat(m[0]),dec:(m[0].split(".")[1]||"").length});last=m.index+m[0].length;}
  if(!parts.length||(window.matchMedia&&matchMedia("(prefers-reduced-motion: reduce)").matches))return;
  var tail=txt.slice(last), t0=null;
  function f(ts){if(t0===null)t0=ts;var k=Math.min(1,(ts-t0)/900),e=1-Math.pow(1-k,3),o="";
    parts.forEach(function(p){o+=p.pre+(p.v*e).toFixed(p.dec);});el.textContent=o+tail;
    if(k<1)requestAnimationFrame(f);else el.textContent=txt;}
  requestAnimationFrame(f);
}
/* guess first */
var GS={x:null,y:null,rev:false,off:false};
function guessHTML(){
  return '<section class="guess" id="guess"></section>';
}
function drawGuess(){
  var b=$("#guess"); if(!b)return;
  if(GS.off){b.innerHTML='<button class="btn" id="gon">🎯 Try the guessing game</button>';$("#gon").onclick=function(){GS={x:null,y:null,rev:false,off:false};drawGuess();};return;}
  var d=S.defaults.nisar, bi=imgUrl(S,"nisar",d[0]), ai=imgUrl(S,"nisar",d[1]);
  b.innerHTML='<div class="gh"><span class="gk">Guess first</span><h3>'+esc(S.question)+'</h3>'+
   '<p>This is the NISAR image from <b>'+fmt(d[0])+'</b>. <b>Tap on it</b> where you think the biggest change will show up by <b>'+fmt(d[1])+'</b>, then reveal the later image.</p></div>'+
   '<div class="gst" id="gst" style="'+aspectCSS()+'"><img src="'+bi+'" alt="NISAR before image"><img class="gafter" src="'+ai+'" alt="NISAR after image" style="opacity:'+(GS.rev?1:0)+'">'+
   (GS.x!==null?'<div class="gm" style="left:'+GS.x+'%;top:'+GS.y+'%"><i></i><b>Your guess</b></div>':'')+
   '<div class="glab">'+(GS.rev?'After · '+fmt(d[1]):'Before · '+fmt(d[0]))+'</div></div>'+
   '<div class="gctl"><button class="btn go" id="grev">'+(GS.rev?'↩ Back to before':'👁 Reveal the later image')+'</button><button class="btn" id="gskip">Skip</button><span class="gmsg">'+
   (GS.rev?(GS.x!==null?'Compare with your guess, then use the slider below for all dates.':'Use the slider below to explore all dates.'):(GS.x!==null?'Guess placed. Move it by tapping again.':'No guess yet: tap the image.')) +'</span></div>';
  var st0=$("#gst");
  st0.onclick=function(e){if(GS.rev)return;var r=st0.getBoundingClientRect();GS.x=+((e.clientX-r.left)/r.width*100).toFixed(1);GS.y=+((e.clientY-r.top)/r.height*100).toFixed(1);drawGuess();};
  $("#grev").onclick=function(){GS.rev=!GS.rev;drawGuess();};
  $("#gskip").onclick=function(){GS.off=true;drawGuess();};
}
/* mix the colours yourself */
var MX={site:"th",t:1,r:true,g:true,b:true};
function drawMix(){
  var c=$("#mixbox"); if(!c)return;
  var tags=PSW[MX.site], tg=tags[MX.t], col="rgb("+(MX.r?255:0)+","+(MX.g?255:0)+","+(MX.b?255:0)+")";
  var on=[MX.r?"red (HH)":"",MX.g?"green (HV)":"",MX.b?"blue (HH − HV)":""].filter(Boolean);
  var msg=!on.length?"All three channels are off, so nothing is left: black.":on.length===3?"All three on: the full colour composite you see in the stories.":"Showing only "+on.join(" + ")+". "+
    (MX.r&&!MX.g&&!MX.b?"Bright where the ground surface or double bounce returns strongly, dark over smooth water.":MX.g&&!MX.r&&!MX.b?"Bright where leaves, branches and stems scatter the signal: vegetation and its water content.":MX.b&&!MX.r&&!MX.g?"Bright where HH is much stronger than HV: bare or smooth ground with little vegetation.":"Switch the others back on to compare.");
  c.innerHTML='<div class="ctl"><div class="seg" role="group" aria-label="Site">'+Object.keys(PSW).map(function(id){return '<button data-mxs="'+id+'" aria-pressed="'+(MX.site===id)+'">'+esc(SITES[id].short)+'</button>';}).join("")+'</div>'+
   '<div class="seg" role="group" aria-label="Moment"><button data-mxt="0" aria-pressed="'+(MX.t===0)+'">Before · '+fmt(tags[0])+'</button><button data-mxt="1" aria-pressed="'+(MX.t===1)+'">After · '+fmt(tags[1])+'</button></div></div>'+
   '<div class="mxrow"><div class="mxstage"><img src="'+imgUrl(SITES[MX.site],"nisar",tg)+'" alt="NISAR composite, '+esc(SITES[MX.site].short)+'"><div class="mxov" style="background:'+col+'"></div></div>'+
   '<div class="mxside"><p class="mxh">Switch the display colours on and off</p>'+
   '<label class="mxc r"><input type="checkbox" data-mxc="r"'+(MX.r?" checked":"")+'><i></i><span><b>Red = HH</b><em>surface, moisture, double bounce</em></span></label>'+
   '<label class="mxc g"><input type="checkbox" data-mxc="g"'+(MX.g?" checked":"")+'><i></i><span><b>Green = HV</b><em>leaves, stems, vegetation water</em></span></label>'+
   '<label class="mxc b"><input type="checkbox" data-mxc="b"'+(MX.b?" checked":"")+'><i></i><span><b>Blue = HH − HV</b><em>how much HH beats HV</em></span></label>'+
   '<p class="mxmsg">'+esc(msg)+'</p></div></div>';
  $$("[data-mxs]",c).forEach(function(b){b.onclick=function(){MX.site=b.dataset.mxs;drawMix();};});
  $$("[data-mxt]",c).forEach(function(b){b.onclick=function(){MX.t=+b.dataset.mxt;drawMix();};});
  $$("[data-mxc]",c).forEach(function(b){b.onchange=function(){MX[b.dataset.mxc]=b.checked;drawMix();};});
}

/* ---------------- SITE ---------------- */
function renderSite(id){
  S=SITES[id]; if(!S){location.hash="#/";return;}
  stopPlay();
  var d=S.defaults;
  st={mode:"cmp",sensor:"nisar",before:d.nisar[0],after:d.nisar[1],pos:50,chg:-1,
      tri:{tags:{nisar:d.nisar[1],s1:d.s1[1],s2:d.s2[1]},z:1,tx:0,ty:0,which:"after"}};
  var idx=ORDER.indexOf(id), prev=SITES[ORDER[(idx+ORDER.length-1)%ORDER.length]], next=SITES[ORDER[(idx+1)%ORDER.length]];
  var statsH=S.stats.map(function(s){return '<div class="stat"><b>'+esc(s[0])+'</b><span>'+esc(s[1])+'</span></div>';}).join("");
  var seeH=S.see.map(function(x){return "<li>"+esc(x)+"</li>";}).join("");
  var limH=S.limits.map(function(x){return "<li>"+esc(x)+"</li>";}).join("");
  var dataH=S.data.map(function(x){return "<tr><td>"+esc(x[0])+"</td><td>"+esc(x[1])+"</td></tr>";}).join("");
  app.innerHTML='<div class="site">'+
   '<div class="crumb"><a href="#/">Home</a> › <span>'+esc(S.country)+'</span> › <span>'+esc(S.group)+'</span></div>'+
   '<div class="shead"><div class="tag">'+esc(S.country)+' · '+esc(S.group)+'</div><h1>'+esc(S.title)+'</h1><div class="place">'+esc(S.place)+'</div>'+mapBtn(id)+'</div>'+
   '<div class="headline"><p>'+esc(S.headline)+'</p></div><div class="stats">'+statsH+'</div>'+
   '<div class="explorer"><div class="ctl" id="ctl1"></div><div id="exp"></div></div>'+
   polBand(id)+tabsHTML(id)+
   '<div class="chartbox"><div class="in"><h3>Time series</h3><p class="cap">'+esc(S.chart.yLabel)+'. Click a point to move the “after” date there. Bars at the bottom are rain.</p><div id="chart"></div><div class="legendrow" id="clegend"></div></div></div>'+
   '<div class="nextrow"><a class="btn" href="#/site/'+prev.id+'" style="text-decoration:none">← '+esc(prev.short)+'</a><a class="btn" href="#/" style="text-decoration:none">All stories</a><a class="btn" href="#/site/'+next.id+'" style="text-decoration:none">'+esc(next.short)+' →</a></div>'+footer()+'</div><div class="tip" id="tip"></div>';
  drawAll(); wireTabs(); $$('.stat b').forEach(countUp); window.scrollTo(0,0);
}
function tagsOf(k){return S.tags[k]||[];}
function aspectCSS(){var w=S.aspect[0],h=S.aspect[1];var vh=document.body.classList.contains("present")?66:70;return "aspect-ratio:"+w+"/"+h+";width:min(100%,calc("+vh+"vh*"+(w/h).toFixed(4)+"))";}
function optList(tags,sel){return tags.map(function(t){return '<option value="'+t+'"'+(t===sel?" selected":"")+'>'+fmt(t)+'</option>';}).join("");}

function drawAll(){drawCtl();drawExplorer();drawChart();}
function drawCtl(){
  var c=$("#ctl1");
  var m='<div class="seg" role="group" aria-label="View"><button data-m="cmp" aria-pressed="'+(st.mode==="cmp")+'">Before / after</button><button data-m="tri" aria-pressed="'+(st.mode==="tri")+'">Three sensors</button></div>';
  var h=m;
  if(st.mode==="cmp"){
    h+='<div class="seg" role="group" aria-label="Sensor">'+["nisar","s1","s2"].map(function(k){return '<button data-s="'+k+'" aria-pressed="'+(st.sensor===k)+'">'+SENS[k].short+'</button>';}).join("")+'</div>';
    var tg=tagsOf(st.sensor);
    if(st.sensor==="s2"&&tg.length===1){h+='<span class="one">One usable optical image (cloud blocked the rest)</span>';}else{
    h+='<label>Before <select id="selB">'+optList(tg,st.before)+'</select></label><label>After <select id="selA">'+optList(tg,st.after)+'</select></label>';
    h+='<button class="btn" id="play" aria-pressed="false">▶ Time-lapse</button>';}
    if(S.changes.length&&st.sensor==="nisar"){
      h+='<label>Change layer <select id="selC"><option value="-1">off</option>'+S.changes.map(function(x,i){return '<option value="'+i+'"'+(st.chg===i?" selected":"")+'>'+esc(x.label)+'</option>';}).join("")+'</select></label>';
    }
  }else{
    h+='<div class="seg" role="group" aria-label="Moment"><button data-w="before" aria-pressed="'+(st.tri.which==="before")+'">Before</button><button data-w="after" aria-pressed="'+(st.tri.which==="after")+'">After</button></div>';
    h+='<button class="btn" id="zin">＋ zoom</button><button class="btn" id="zout">－ zoom</button><button class="btn" id="zreset">Reset view</button>';
  }
  c.innerHTML=h;
  $$("[data-m]",c).forEach(function(b){b.onclick=function(){stopPlay();st.mode=b.dataset.m;if(st.mode==="tri")syncTri();drawAll();};});
  $$("[data-s]",c).forEach(function(b){b.onclick=function(){stopPlay();setSensor(b.dataset.s);};});
  $$("[data-w]",c).forEach(function(b){b.onclick=function(){st.tri.which=b.dataset.w;syncTri();drawAll();};});
  var sb=$("#selB",c),sa=$("#selA",c),sc=$("#selC",c);
  if(sb)sb.onchange=function(){stopPlay();st.before=sb.value;drawExplorer();drawChartMarks();};
  if(sa)sa.onchange=function(){stopPlay();st.after=sa.value;drawExplorer();drawChartMarks();};
  if(sc)sc.onchange=function(){st.chg=+sc.value;if(st.chg>=0){var x=S.changes[st.chg];st.before=x.before;st.after=x.after;}drawAll();};
  var pl=$("#play",c); if(pl)pl.onclick=togglePlay;
  var zi=$("#zin",c),zo=$("#zout",c),zr=$("#zreset",c);
  if(zi)zi.onclick=function(){zoomAt(.5,.5,1.4);};
  if(zo)zo.onclick=function(){zoomAt(.5,.5,1/1.4);};
  if(zr)zr.onclick=function(){st.tri.z=1;st.tri.tx=0;st.tri.ty=0;applyTri();};
}
function setSensor(k){
  var tg=tagsOf(k), dd=S.defaults[k];
  st.sensor=k; st.chg=-1;
  st.before=tg.indexOf(dd[0])>=0?dd[0]:tg[0]; st.after=tg.indexOf(dd[1])>=0?dd[1]:tg[tg.length-1];
  drawAll();
}
function syncTri(){
  var base=st.tri.which==="before"?S.defaults.nisar[0]:S.defaults.nisar[1];
  setMoment(iso(base));
}
function setMoment(isoDate){
  ["nisar","s1","s2"].forEach(function(k){var tg=tagsOf(k);if(tg.length)st.tri.tags[k]=nearest(tg,isoDate);});
}

/* ---- before/after explorer ---- */
function drawExplorer(){
  var box=$("#exp");
  if(st.mode==="tri"){drawTri(box);return;}
  var k=st.sensor, sn=SENS[k], bT=st.before, aT=st.after, chg=st.chg>=0?S.changes[st.chg]:null;
  var note=function(t){var n=k==="s2"&&S.s2notes[t]?" · "+S.s2notes[t]:"";return fmt(t)+n;};
  var inner="";
  if(chg){
    inner='<img class="base" src="'+imgUrl(S,"nisar",chg.after)+'" alt="NISAR image, '+fmt(chg.after)+'" style="opacity:.55"><img class="chg" src="'+chgUrl(S,chg.file)+'" alt="Change layer, '+esc(chg.label)+'">'+
      '<div class="lab l"><b>Change layer: '+esc(chg.label)+'</b>NISAR L-band, HV</div>';
  }else if(k==="s2"&&tagsOf("s2").length===1){
    inner='<img class="base" src="'+imgUrl(S,k,bT)+'" alt="'+sn.name+', '+fmt(bT)+'">'+
      '<div class="lab l"><b>'+note(bT)+'</b>'+sn.name+'</div>';
  }else{
    inner='<img class="base" src="'+imgUrl(S,k,aT)+'" alt="'+sn.name+', '+fmt(aT)+'">'+
      '<img class="top-img" src="'+imgUrl(S,k,bT)+'" alt="'+sn.name+', '+fmt(bT)+'">'+
      '<div class="lab l" id="labB"><b>Before · '+note(bT)+'</b>'+sn.name+'</div><div class="lab r" id="labA"><b>After · '+note(aT)+'</b>'+sn.name+'</div>'+
      '<div class="handle" id="handle" role="slider" tabindex="0" aria-label="Before and after slider" aria-valuemin="0" aria-valuemax="100" aria-valuenow="50"><i>⇄</i></div><div class="big-date" id="bigd" style="display:none"></div>';
  }
  var one=!chg&&k==="s2"&&tagsOf("s2").length===1;
  var explain=one?(S.id==="mt"?"Only one usable optical image: 13 Oct and 18 Oct, around the event, were fully cloud-covered, so there is no optical \"after\" picture. This is where radar helps. ":"Only one usable optical image: cloud covered the other dates. ")+sn.rec+'. '+sn.note:chg?'Blue = darker than the earlier date (more water-like or smoother), red = brighter. Colour appears only where the change passes the site threshold (about 2–3 dB).':sn.rec+'. '+sn.note;
  box.innerHTML='<div class="cmpwrap"><div class="stage" id="stage" style="'+aspectCSS()+'">'+inner+'</div></div><p class="note">'+esc(explain)+'</p>';
  var stage=$("#stage"),h=$("#handle");
  if(!h)return;
  setPos(st.pos);
  var down=false;
  function move(e){var r=stage.getBoundingClientRect();var p=(e.clientX-r.left)/r.width*100;setPos(Math.max(0,Math.min(100,p)));}
  stage.onpointerdown=function(e){stopPlay();down=true;stage.setPointerCapture(e.pointerId);move(e);};
  stage.onpointermove=function(e){if(down)move(e);};
  stage.onpointerup=stage.onpointercancel=function(){down=false;};
  h.onkeydown=function(e){if(e.key==="ArrowLeft"){setPos(st.pos-4);e.preventDefault();}if(e.key==="ArrowRight"){setPos(st.pos+4);e.preventDefault();}};
}
function setPos(p){
  p=Math.max(0,Math.min(100,p)); st.pos=p;
  var t=$(".top-img"),h=$("#handle"); if(!t||!h)return;
  t.style.clipPath="inset(0 "+(100-p)+"% 0 0)"; h.style.left=p+"%"; h.setAttribute("aria-valuenow",Math.round(p));
}
/* time-lapse */
function togglePlay(){if(timer)stopPlay();else startPlay();}
function stopPlay(){
  if(timer){clearInterval(timer);timer=null;}
  var b=$("#play"); if(b){b.setAttribute("aria-pressed","false");b.textContent="▶ Time-lapse";}
  var bd=$("#bigd"); if(bd)bd.style.display="none";
  var lb=$("#labB"),la=$("#labA"),h=$("#handle"); if(lb)lb.style.display="";if(la)la.style.display="";if(h)h.style.display="";
}
function startPlay(){
  if(st.mode!=="cmp"||st.chg>=0)return;
  var tg=tagsOf(st.sensor); if(tg.length<2)return;
  var i=0, k=st.sensor, sn=SENS[k];
  var b=$("#play"); b.setAttribute("aria-pressed","true"); b.textContent="❚❚ Pause";
  var lb=$("#labB"),la=$("#labA"),h=$("#handle"),bd=$("#bigd");
  lb.style.display="none";la.style.display="none";h.style.display="none";bd.style.display="block";
  function frame(){
    var t=tg[i], base=$(".base"), top=$(".top-img");
    base.src=imgUrl(S,k,t); top.style.clipPath="inset(0 100% 0 0)";
    bd.textContent=sn.short+" · "+fmt(t)+(k==="s2"&&S.s2notes[t]?" · "+S.s2notes[t]:"")+"  ("+(i+1)+"/"+tg.length+")";
    st.after=t; drawChartMarks(t);
    i++; if(i>=tg.length){clearInterval(timer);timer=null;setTimeout(function(){stopPlay();drawAll();},1100);}
  }
  frame(); timer=setInterval(frame,1000);
}

/* ---- three-sensor view ---- */
function drawTri(box){
  var kinds=["nisar","s1","s2"], nT=st.tri.tags.nisar, nd=dnum(iso(nT));
  var html='<div class="three-s">';
  kinds.forEach(function(k){
    var tg=tagsOf(k), t=st.tri.tags[k], gap=Math.round(dnum(iso(t))-nd);
    var gapT=k==="nisar"?"":(gap===0?" · same day as NISAR":" · "+Math.abs(gap)+" day"+(Math.abs(gap)===1?"":"s")+(gap<0?" before":" after")+" NISAR");
    var nt=k==="s2"&&S.s2notes[t]?" · "+S.s2notes[t]:"";
    html+='<div class="panel"><h4 style="color:'+SENS[k].col+'">'+SENS[k].name+'</h4>'+
      '<div class="vp" data-k="'+k+'" style="aspect-ratio:'+S.aspect[0]+'/'+S.aspect[1]+'"><div class="inner"><img src="'+imgUrl(S,k,t)+'" alt="'+SENS[k].name+', '+fmt(t)+'"></div><div class="xh h"></div><div class="xh v"></div><div class="cb">'+SENS[k].short+' · '+fmt(t)+nt+'</div></div>'+
      '<label style="font-size:13px;color:var(--muted);display:block;margin-top:6px">Date <select data-k="'+k+'" class="tsel">'+optList(tg,t)+'</select><span style="margin-left:6px">'+esc(gapT)+'</span></label>'+
      '<div class="pn">'+esc(SENS[k].rec)+'. '+esc(SENS[k].note)+'</div></div>';
  });
  html+='</div><p class="note">Same ground, same frame. Scroll or use the zoom buttons to zoom, drag to pan, and the crosshair follows your cursor in all three. Click a point on the time series to move all three to that date.</p>';
  box.innerHTML=html;
  $$(".tsel",box).forEach(function(s){s.onchange=function(){st.tri.tags[s.dataset.k]=s.value;drawTri(box);drawChartMarks();};});
  var vps=$$(".vp",box), drag=null;
  vps.forEach(function(vp){
    vp.onwheel=function(e){e.preventDefault();var r=vp.getBoundingClientRect();zoomAt((e.clientX-r.left)/r.width,(e.clientY-r.top)/r.height,e.deltaY<0?1.25:1/1.25);};
    vp.onpointerdown=function(e){vp.setPointerCapture(e.pointerId);drag={x:e.clientX,y:e.clientY,tx:st.tri.tx,ty:st.tri.ty,r:vp.getBoundingClientRect()};};
    vp.onpointermove=function(e){
      var r=vp.getBoundingClientRect(),u=(e.clientX-r.left)/r.width,v=(e.clientY-r.top)/r.height;
      vps.forEach(function(o){var h=$(".xh.h",o),vv=$(".xh.v",o);h.style.display=vv.style.display="block";h.style.top=(v*100)+"%";vv.style.left=(u*100)+"%";});
      if(drag){st.tri.tx=drag.tx+(e.clientX-drag.x)/drag.r.width;st.tri.ty=drag.ty+(e.clientY-drag.y)/drag.r.height;applyTri();}
    };
    vp.onpointerup=vp.onpointercancel=function(){drag=null;};
    vp.onpointerleave=function(){vps.forEach(function(o){$(".xh.h",o).style.display=$(".xh.v",o).style.display="none";});};
  });
  applyTri();
}
function clampTri(){var z=st.tri.z;st.tri.tx=Math.min(0,Math.max(1-z,st.tri.tx));st.tri.ty=Math.min(0,Math.max(1-z,st.tri.ty));}
function applyTri(){
  clampTri();
  $$(".vp .inner").forEach(function(el){el.style.transform="translate("+(st.tri.tx*100)+"%,"+(st.tri.ty*100)+"%) scale("+st.tri.z+")";});
}
function zoomAt(u,v,f){
  var t=st.tri, z2=Math.max(1,Math.min(8,t.z*f)); if(z2===t.z)return;
  var px=(u-t.tx)/t.z, py=(v-t.ty)/t.z; t.z=z2; t.tx=u-px*z2; t.ty=v-py*z2; applyTri();
}

/* ---- chart ---- */
var CH={W:900,H:560,L:74,R:14,T:12,PB:214,RT:252,RB:502};
function drawChart(){
  var c=S.chart, D0=dnum("2026-06-15"), D1=dnum("2026-10-31");
  var xs=function(d){return CH.L+(dnum(d)-D0)/(D1-D0)*(CH.W-CH.L-CH.R);};
  var vals=[]; c.series.forEach(function(s){s.pts.forEach(function(p){vals.push(p[1]);});}); if(c.band)vals.push(c.band.hi);
  var ymax=Math.max.apply(null,vals)*1.1, step=niceStep(ymax/4), top=Math.ceil(ymax/step)*step;
  var ys=function(v){return CH.PB-(v/top)*(CH.PB-CH.T);};
  var o='<svg class="chart" viewBox="0 0 '+CH.W+' '+CH.H+'" role="img" aria-label="'+esc(c.yLabel)+'">';
  for(var v=0;v<=top+1e-9;v+=step){o+='<line x1="'+CH.L+'" x2="'+(CH.W-CH.R)+'" y1="'+ys(v)+'" y2="'+ys(v)+'" stroke="#243357" stroke-width="1"/><text x="'+(CH.L-6)+'" y="'+(ys(v)+4)+'" text-anchor="end">'+(step<1?v.toFixed(1):Math.round(v*10)/10)+'</text>';}
  [["2026-07-01","Jul"],["2026-08-01","Aug"],["2026-09-01","Sep"],["2026-10-01","Oct"]].forEach(function(m){o+='<line x1="'+xs(m[0])+'" x2="'+xs(m[0])+'" y1="'+CH.T+'" y2="'+CH.RB+'" stroke="#1a2745" stroke-width="1"/><text x="'+(xs(m[0])+4)+'" y="'+(CH.RB+16)+'">'+m[1]+'</text>';});
  if(c.band)o+='<rect x="'+CH.L+'" width="'+(CH.W-CH.L-CH.R)+'" y="'+ys(c.band.hi)+'" height="'+(ys(c.band.lo)-ys(c.band.hi))+'" fill="#4cc9f0" opacity=".13"/><text x="'+(CH.W-CH.R-4)+'" y="'+(ys(c.band.hi)-4)+'" text-anchor="end" style="fill:#7fd6f3">'+esc(c.band.label)+'</text>';
  (c.events||[]).forEach(function(e){var x=xs(e.date);o+='<line x1="'+x+'" x2="'+x+'" y1="'+CH.T+'" y2="'+CH.PB+'" stroke="#f4a259" stroke-dasharray="4 3"/><text x="'+(x+4)+'" y="'+(CH.T+11)+'" style="fill:#f4a259">'+esc(e.label)+'</text>';});
  /* rain */
  var rmax=1,rb=[]; (c.rain||[]).forEach(function(r){var span=Math.max(1,dnum(r.d1)-dnum(r.d0));var per=r.d0===r.d1?r.mm:r.mm/span;rb.push([r,per,span]);if(per>rmax)rmax=per;});
  if(rb.length){
    var rtop=(rmax>40?20:rmax>10?5:1)*Math.ceil(rmax/(rmax>40?20:rmax>10?5:1)), rh=CH.RB-CH.RT;
    o+='<text x="'+(CH.L-6)+'" y="'+(CH.RT+8)+'" text-anchor="end">'+rtop+'</text><text x="'+(CH.L-6)+'" y="'+CH.RB+'" text-anchor="end">0</text><text x="'+(CH.L+2)+'" y="'+(CH.RT-4)+'">rain, mm per day (model)</text>';
    rb.forEach(function(q){var r=q[0],per=q[1],x0,w;
      if(r.d0===r.d1){x0=xs(r.d0)-1.5;w=Math.max(1.5,(CH.W-CH.L-CH.R)/(D1-D0)*.9);}else{x0=xs(r.d0);w=Math.max(1,xs(r.d1)-xs(r.d0)-1);}
      var hh=per/rtop*rh; o+='<rect x="'+x0.toFixed(1)+'" y="'+(CH.RB-hh).toFixed(1)+'" width="'+w.toFixed(1)+'" height="'+hh.toFixed(1)+'" fill="#7fa8e8" opacity=".9"><title>'+fmtIso(r.d0)+(r.d0===r.d1?"":" → "+fmtIso(r.d1))+': '+Math.round(r.mm)+' mm</title></rect>';});
  }
  o+=ytitle(15,(CH.T+CH.PB)/2,YSHORT[Object.keys(SITES).filter(function(k){return SITES[k]===S;})[0]]||'Area (km²)');
  if(rb.length)o+=ytitle(15,(CH.RT+CH.RB)/2,'Rain (mm per day)');
  o+=xtitle((CH.L+CH.W-CH.R)/2,CH.RB+38,'Date, 2026');
  c.series.forEach(function(s,si){
    var col=s.color||SENS[s.sensor].col;
    o+='<polyline fill="none" stroke="'+col+'" stroke-width="2" points="'+s.pts.map(function(p){return xs(p[0]).toFixed(1)+","+ys(p[1]).toFixed(1);}).join(" ")+'"/>';
    s.pts.forEach(function(p){o+='<circle class="pt" data-d="'+p[0]+'" data-v="'+p[1]+'" data-s="'+esc(s.label)+'" cx="'+xs(p[0]).toFixed(1)+'" cy="'+ys(p[1]).toFixed(1)+'" r="5" fill="'+col+'" stroke="#060a16" stroke-width="1.5"/>';});
  });
  o+='<g id="marks" style="pointer-events:none"></g></svg>';
  $("#chart").innerHTML=o;
  $("#clegend").innerHTML=c.series.map(function(s){return '<span><i style="background:'+(s.color||SENS[s.sensor].col)+'"></i>'+esc(s.label)+'</span>';}).join("")+'<span><i style="background:#6f8fc4"></i>rain (MERRA-2 model)</span>';
  var tip=$("#tip");
  $$("#chart .pt").forEach(function(p){
    p.onmousemove=function(e){tip.style.display="block";tip.style.left=(e.clientX+12)+"px";tip.style.top=(e.clientY+12)+"px";tip.innerHTML="<b>"+fmtIso(p.dataset.d)+"</b><br>"+esc(p.dataset.s)+": "+(+p.dataset.v).toFixed(+p.dataset.v<10?2:1);};
    p.onmouseleave=function(){tip.style.display="none";};
    p.onclick=function(){chartClick(p.dataset.d);};
  });
  S._xs=xs; drawChartMarks();
}
function ytitle(x,y,t){return '<text transform="rotate(-90 '+x+' '+y+')" x="'+x+'" y="'+y+'" text-anchor="middle" style="font-size:11.5px">'+t+'</text>';}
function xtitle(x,y,t){return '<text x="'+x+'" y="'+y+'" text-anchor="middle" style="font-size:11.5px">'+t+'</text>';}
var YSHORT={th:"Water-like area (km²)",as:"Newly dark area (km²)",dv:"Newly dark area (km²)",mt:"Dark land area (km²)",mn:"Dark area (km²)",sn:"Dark share of outline (%)",pt:"Pixels changed (%)"};
function niceStep(x){var e=Math.pow(10,Math.floor(Math.log10(x))),f=x/e;return (f<=1?1:f<=2?2:f<=5?5:10)*e;}
function chartClick(isoD){
  stopPlay();
  if(st.mode==="tri"){setMoment(isoD);drawAll();return;}
  var tg=tagsOf(st.sensor); var t=nearest(tg,isoD); st.after=t; st.chg=-1; drawAll();
}
function drawChartMarks(playTag){
  var g=$("#marks"); if(!g||!S._xs)return; var xs=S._xs, o="";
  var lastX=null;
  var line=function(d,col,dash,lab){var x=xs(d),right=x>CH.W-CH.R-70,ly=CH.PB-4;
    if(lastX!=null&&Math.abs(x-lastX)<64)ly=CH.PB-20; lastX=x;
    return '<line x1="'+x+'" x2="'+x+'" y1="'+CH.T+'" y2="'+CH.PB+'" stroke="'+col+'" stroke-width="1.5" '+(dash?'stroke-dasharray="5 4"':"")+'/><rect x="'+(right?x-8-lab.length*7:x+2)+'" y="'+(ly-13)+'" width="'+(lab.length*7+6)+'" height="17" rx="3" fill="#0b1224" fill-opacity=".85"/><text x="'+(right?x-5:x+5)+'" y="'+ly+'" text-anchor="'+(right?"end":"start")+'" style="fill:'+col+';font-weight:600">'+lab+'</text>';};
  if(st.mode==="cmp"&&st.chg<0){
    if(!timer)o+=line(iso(st.before),"#ffffff",true,"before");
    o+=line(iso(playTag||st.after),"#4cc9f0",false,"after");
  }else if(st.mode==="tri"){
    o+=line(iso(st.tri.tags.nisar),"#4cc9f0",false,"NISAR");
  }else if(st.chg>=0){o+=line(iso(st.before),"#ffffff",true,"before")+line(iso(st.after),"#4cc9f0",false,"after");}
  g.innerHTML=o;
}


/* ---------------- POLARIZATIONS ---------------- */
/* Pixel counts from hhhv_check.py (NISAR GCOV HHHH/HVHV, 9x9 smoothed, median-aligned, 3 dB threshold).
   dk/br = [HH, HV] pixels darker / brighter than the earlier date; both = pixels darker in both; v = valid pixels. */
var PD={
 th:{v:230400,dk:[68236,23598],br:[24503,3042],both:20946,pair:"25 Aug → 30 Sep",m:"dk"},
 as:{v:614400,dk:[68591,47090],br:[3518,924],both:43539,pair:"10 Jul → 22 Jul",m:"dk"},
 mt:{v:960000,dk:[10625,5503],br:[619,915],both:5040,pair:"12 Sep → 24 Sep",m:"dk"},
 dv:{v:259015,dk:[7747,8474],br:[1848,443],both:4802,pair:"19 Aug → 31 Aug",m:"dk"},
 pt:{v:360000,dk:[17436,20746],br:[15737,19439],both:10065,pair:"14 Jul → 19 Aug",m:"dk"},
 mn:{v:466947,dk:[3529,3],br:[2362,23550],both:0,pair:"2 Jul → 18 Oct",m:"br"},
 sn:{v:714393,dk:[1363,113],br:[11601,3016],both:14,pair:"2 Jul → 18 Oct",m:"br"}
};
var PG=[
 {t:"Flood water or wet ground",ids:["th","as","mt"],txt:"HH marked the darkening over a larger share of the box than HV did, and roughly 9 in 10 of the pixels HV flagged were also darker in HH. Consistent with HH being the more sensitive channel for smooth water and wet ground, with HV the stricter test."},
 {t:"Vegetation, sediment and tank fields",ids:["dv","mn"],txt:"Devighat: both channels flagged similar areas, HV slightly more, and only about half the HV-darker pixels were also darker in HH. Minneriya: HV brightened over about ten times the share HH did. Consistent with HV following vegetation and ground cover more than water."},
 {t:"Built surfaces",ids:["pt"],txt:"Both channels changed, in both directions, and only about half the HV-darker pixels were also darker in HH. For containers, cranes and reclaimed land the two channels need to be read together."},
 {t:"Brightening with HH ahead",ids:["sn"],txt:"HH brightened over about four times the share HV did. We have not confirmed the cause, so we do not name one."}
];
var PSW={th:["aug25","sep30"],as:["jul10","jul22"],dv:["aug19","aug31"]};
var ps={mode:"dk",site:"th",t:1,ch:"comp"};
function pct(n,v){var x=100*n/v;return x<0.01&&n>0?"<0.01%":x>=10?x.toFixed(0)+"%":x>=1?x.toFixed(1)+"%":x.toFixed(2)+"%";}
function pctV(n,v){return 100*n/v;}
function ratioTxt(a,b,v){
  var A=pctV(a,v),B=pctV(b,v);
  if(Math.max(A,B)<0.05)return "both small";
  if(B<0.03*A||b<30)return "only HH changed";
  if(A<0.03*B||a<30)return "only HV changed";
  var r=A/B; return r>=1.15?"HH "+r.toFixed(1)+"× HV":r<=1/1.15?"HV "+(1/r).toFixed(1)+"× HH":"about equal";
}
function polBand(id){
  var d=PD[id]; if(!d)return "";
  var k=d.m==="dk"?"dk":"br", w=d.m==="dk"?"darker":"brighter";
  return '<div class="polband"><div><b>Which radar channel showed it?</b> NISAR, '+d.pair+': HH got '+w+' by more than 3 dB over <span class="chh">'+pct(d[k][0],d.v)+'</span> of the box and HV over <span class="chv">'+pct(d[k][1],d.v)+'</span> ('+ratioTxt(d[k][0],d[k][1],d.v)+').</div><a class="btn" href="#/polar/'+id+'" style="text-decoration:none">Compare all seven sites →</a></div>';
}
function polImg(){
  var tags=PSW[ps.site],tag=tags[ps.t];
  return ps.ch==="comp"?"img/"+ps.site+"_nisar_"+tag+".webp":"img/pol_"+ps.site+"_"+ps.ch+"_"+tag+".webp";
}
function polRows(hl){
  var k=ps.mode, h="";
  PG.forEach(function(g){
    h+='<div class="pgrp"><h3>'+esc(g.t)+'</h3><p>'+esc(g.txt)+'</p>';
    g.ids.forEach(function(id){
      var d=PD[id],s=SITES[id],a=d[k][0],b=d[k][1],mx=Math.max(a,b,1);
      var agree=(k==="dk"&&(d.dk[1]>=1000))?'<span>'+Math.round(100*d.both/d.dk[1])+'% of HV-darker pixels also darker in HH</span>':'';
      h+='<a class="prow'+(hl===id?" hl":"")+'" id="pr_'+id+'" href="#/site/'+id+'"><div class="pn"><b>'+esc(s.short)+'</b><span>'+esc(s.country)+' · '+d.pair+'</span></div>'+
        '<div class="pb"><div class="bar hh"><i style="width:'+Math.max(a>0?0.8:0,100*a/mx).toFixed(1)+'%"></i><em>HH '+pct(a,d.v)+'</em></div>'+
        '<div class="bar hv"><i style="width:'+Math.max(b>0?0.8:0,100*b/mx).toFixed(1)+'%"></i><em>HV '+pct(b,d.v)+'</em></div></div>'+
        '<div class="pa"><b>'+ratioTxt(a,b,d.v)+'</b>'+agree+'</div></a>';
    });
    h+='</div>';
  });
  return h;
}
function drawPolSwitch(){
  var c=$("#psw"); if(!c)return;
  var tags=PSW[ps.site];
  var h='<div class="ctl"><div class="seg" role="group" aria-label="Site">'+Object.keys(PSW).map(function(id){return '<button data-ps="'+id+'" aria-pressed="'+(ps.site===id)+'">'+esc(SITES[id].short)+'</button>';}).join("")+'</div>'+
   '<div class="seg" role="group" aria-label="Moment"><button data-pt="0" aria-pressed="'+(ps.t===0)+'">Before · '+fmt(tags[0])+'</button><button data-pt="1" aria-pressed="'+(ps.t===1)+'">After · '+fmt(tags[1])+'</button></div>'+
   '<div class="seg" role="group" aria-label="Channel"><button data-pc="comp" aria-pressed="'+(ps.ch==="comp")+'">Colour composite</button><button data-pc="hh" aria-pressed="'+(ps.ch==="hh")+'" class="bhh">HH only</button><button data-pc="hv" aria-pressed="'+(ps.ch==="hv")+'" class="bhv">HV only</button></div></div>'+
   '<div class="pimg"><img id="pimg" src="'+polImg()+'" alt="NISAR radar image, '+esc(SITES[ps.site].short)+'"><div class="pmiss" id="pmiss" hidden>This channel image has not been added yet.</div></div>'+
   '<p class="cap">NISAR L-band, provisional. HH is shown in red and HV in green, the same colour code as the composite. Each channel uses one fixed stretch for both dates, so brightness can be compared between before and after. Flip between the three views on the same ground.</p>';
  c.innerHTML=h;
  $$("[data-ps]",c).forEach(function(b){b.onclick=function(){ps.site=b.dataset.ps;drawPolSwitch();};});
  $$("[data-pt]",c).forEach(function(b){b.onclick=function(){ps.t=+b.dataset.pt;drawPolSwitch();};});
  $$("[data-pc]",c).forEach(function(b){b.onclick=function(){ps.ch=b.dataset.pc;drawPolSwitch();};});
  var im=$("#pimg",c); im.onerror=function(){im.style.visibility="hidden";$("#pmiss",c).hidden=false;};
  im.onload=function(){im.style.visibility="visible";$("#pmiss",c).hidden=true;};
}
function ctile(k,name,txt,where){return '<figure class="ct"><img src="img/ex_'+k+'.webp" alt="'+esc(name)+' example" ><figcaption><b>'+esc(name)+'</b><span>'+esc(txt)+'</span><em>'+esc(where)+'</em></figcaption></figure>';}

/* ---------------- RVI panel (Polarizations page) ---------------- */
var RVP=[
 {k:"nw",n:"Nawalapitiya",
  main:["rvi_a","Morning pass · track T084A, ascending","Map of mean Radar Vegetation Index at Nawalapitiya, morning pass"],
  more:[["rvi_d","Evening pass · track T048D, descending","Map of mean Radar Vegetation Index at Nawalapitiya, evening pass"],["rvi_nw_ts","Forest-like and changing blocks over time (morning pass)","Chart of median RVI over time for forest-like and changing blocks at Nawalapitiya, morning pass"]],
  pat:"Dark green blocks are forest-like. Paler blocks are more open, less vegetated ground.",
  forest:"Forest-like blocks stay near 1 all season (about 1.02–1.06).",
  res:"Vegetation density is steady: the box median RVI stays between 0.87 and 0.91 (morning pass) and 0.88 and 0.90 (evening pass), and only 2.7% and 3.3% of blocks change by 0.15 or more. The same scenes show large wetness changes with rain (see the Rain test), so wetness and vegetation can be told apart. We make no growth claim here.",
  c:"The morning-pass forest-like median rises by about 0.03 in early October. We read this as within the range of processing and weather effects, not growth."},
 {k:"am",n:"Ampara",
  main:["rvi_am_a","Morning pass · track T156A, ascending","Map of mean Radar Vegetation Index at Ampara, morning pass"],
  more:[["rvi_am_d","Evening pass · track T120D, descending (mean only)","Map of mean Radar Vegetation Index at Ampara, evening pass"],["rvi_am_chg","RVI change, last third minus first third of the season (morning pass)","Map of Radar Vegetation Index change at Ampara, morning pass"],["rvi_am_split","Reproducibility test: HV − HH of blocks chosen on odd dates (morning pass)","Chart of HV minus HH over time for blocks chosen on odd dates, with a stable control"],["rvi_am_wet","Wetness vs daily rain, morning pass: r 0.49 with 7-day rain, n = 10, not significant on its own","Chart of the wetness index against daily rain at Ampara, morning pass"]],
  pat:"Dark green blocks are forest-like. The paler river-valley lowland has much lower RVI.",
  forest:"Forest-like blocks stay flat all season (about 1.04–1.07).",
  res:"In the river-valley blocks that change, RVI rises from about 0.6 (7 Jul) to 0.75 (24 Aug), then eases to about 0.69. Blocks chosen on the odd dates only (4,332 blocks, 6.1% of the land) rise by 1.45 dB in HV − HH on the even dates not used for choosing, against 0.03 dB for a forest control, and 76% reproduce it. This is consistent with crop growth in cultivated land.",
  c:"Crop type, planting dates and harvest dates are not identified. The 23 Oct scene is a validated product with no offset applied; the forest control shows no step on that date. The evening pass changes to a different radar mode (20 m quad-pol) on 21 Aug, so only its mean map is shown. White areas are masked."},
 {k:"rn",n:"Ratnapura",
  main:["rvi_rn_a","Morning pass · track T084A, ascending","Map of mean Radar Vegetation Index at Ratnapura, morning pass"],
  more:[["rvi_rn_ts","Forest-like and changing blocks over time (morning pass)","Chart of median RVI over time for forest-like and changing blocks at Ratnapura, morning pass"]],
  pat:"Dark green blocks are forest-like. Paler blocks are more open, less vegetated ground.",
  forest:"Forest-like blocks stay near 1 all season (about 1.04–1.07).",
  res:"Vegetation is steady: the box median RVI stays between 0.89 and 0.92 and only 1.7% of blocks change by 0.15 or more. The small drift (about 0.03) is within what the processing offsets can produce, so we call it stable, not growth.",
  c:"The evening pass was not analysed for this site. Validated scenes (30 Oct, 11 Nov) have offsets applied (HH +0.35, HV +0.11 dB)."}
];
var rvS={p:"nw"};
function rvFig(x){return '<figure><img src="img/'+x[0]+'.webp" alt="'+esc(x[2])+'" loading="lazy"><figcaption>'+esc(x[1])+'</figcaption></figure>';}
function drawRv(){
  var r=RVP.filter(function(x){return x.k===rvS.p;})[0]||RVP[0];
  $("#rvbox").innerHTML='<div class="rvmain">'+rvFig(r.main)+'<div class="rvtxt"><p><b>What it shows.</b> '+esc(r.pat)+'</p><p><b>Through the season.</b> '+esc(r.forest)+'</p><p><b>Result.</b> '+esc(r.res)+'</p>'+
   '<p class="rc"><b>Read with care.</b> '+(r.c?esc(r.c)+' ':'')+'A relative density, not biomass; the scale is not a strict 0 to 1, because forest-like blocks sit near 1.</p></div></div>'+
   (r.more.length?'<details class="faq rvmore"><summary>More maps and tests for '+esc(r.n)+' ('+r.more.length+')</summary><div class="rvi2">'+r.more.map(rvFig).join("")+'</div></details>':'<p class="rc">No further maps for this site.</p>');
  $$("[data-rvp]").forEach(function(b){b.setAttribute("aria-pressed",b.dataset.rvp===r.k?"true":"false");});
}
function renderPolar(hl){
  stopPlay(); document.body.classList.remove("site-open");
  if(hl&&PD[hl]){ps.mode=PD[hl].m;if(PSW[hl])ps.site=hl;}
  app.innerHTML='<div class="site polar">'+
   '<div class="crumb"><a href="#/">Home</a> › <span>Polarizations</span></div>'+
   '<div class="shead"><div class="tag">Which polarizations highlight these changes?</div><h1>HH and HV: which channel shows what</h1><div class="place">NISAR sends and receives radar in two combinations. Each answers to different things on the ground.</div></div>'+
   '<div class="pcards"><div class="pc hh"><h3><i></i>HH (red)</h3><p>Sent and received horizontally. Responds to the ground surface (roughness and moisture) and to the double bounce off structures, tree trunks and flooded plants. Smooth open water returns very little, so it looks dark.</p></div>'+
   '<div class="pc hv"><h3><i></i>HV (green)</h3><p>Sent horizontally, received vertically. Responds to scattering inside leaves, branches and stems, so it follows vegetation and its water content.</p></div></div>'+
   '<section class="psec"><h2>How the colours are made</h2><p class="sub">Every pixel in a NISAR picture gets three numbers. Each one drives one display colour, and the mix is what you see.</p>'+
   '<div class="mix"><div class="mx r"><b>Red</b><span>HH</span></div><div class="op">+</div><div class="mx g"><b>Green</b><span>HV</span></div><div class="op">+</div><div class="mx b"><b>Blue</b><span>HH − HV</span></div><div class="op">=</div><div class="mx o"><b>One colour</b><span>per pixel</span></div></div>'+
   '<p class="cap" style="margin-top:8px">These are display colours (NASA SVS 5661 recipe), not the colour of the ground. Blue is the gap between HH and HV: it is large when HH is much stronger than HV.</p>'+
   '<div class="ctiles">'+
   ctile("veg","Green to yellow","Strong HV: leaves and stems scatter the signal back. Adding some HH turns green to yellow.","Vegetation or crops · Thailand, 30 Sep")+
   ctile("bare","Purple","Strong HH, weak HV, big gap between them: little vegetation scattering. Consistent with smooth or bare ground.","Fields before flooding · Thailand, 25 Aug")+
   ctile("dark","Black","Every channel weak. Consistent with a very smooth, water-covered surface, or radar shadow.","Fields after the rise · Thailand, 30 Sep")+
   ctile("bld","Pink to white","All three strong. Typical of hard structures that bounce the signal back, and of flooded vegetation.","Container stacks · Colombo Port, 14 Jul")+
   ctile("sea","Deep blue-violet","Weak in both channels. Calm sea looks like this, so very smooth surfaces can be black or blue-violet depending on the stretch.","Calm sea · Colombo Port, 14 Jul")+
   '</div><p class="cap">Each story uses one fixed stretch for all its dates, so colours can be compared between dates in the same story. Colours are a guide to the surface, not proof of what it is.</p></section>'+
   '<section class="psec"><h2>Mix the colours yourself</h2><p class="sub">Turn each display colour on or off and watch what is left. This shows what each radar channel adds.</p><div id="mixbox"></div></section>'+
   '<section class="psec"><h2>See it on the same ground</h2><p class="sub">Pick a story, then flip between the colour composite, HH only and HV only.</p><div id="psw"></div></section>'+
   '<section class="psec"><h2>How much each channel changed, in seven stories</h2><p class="sub">Share of each study box that changed by more than 3 dB between the two dates shown. Each row is scaled to its larger bar, so compare HH with HV within a row. Click a row to open the story.</p>'+
   '<div class="ctl"><div class="seg" role="group" aria-label="Direction"><button data-pm="dk" aria-pressed="'+(ps.mode==="dk")+'">Got darker</button><button data-pm="br" aria-pressed="'+(ps.mode==="br")+'">Got brighter</button></div><span class="plg"><i class="ihh"></i>HH <i class="ihv"></i>HV</span></div>'+
   '<div id="prows">'+polRows(hl)+'</div>'+
   '<section class="psec" id="rvsec"><h2>What else can HH and HV give? Vegetation density</h2><p class="sub">The Radar Vegetation Index (RVI) is 4 × HV ÷ (HH + HV), worked out in linear power. It shows how much of the signal comes from leaves and branches rather than from the ground surface. Pick a place.</p>'+
   '<div class="roles" role="group" aria-label="Choose a place" id="rvPlace">'+RVP.map(function(r,i){return '<button type="button" data-rvp="'+r.k+'" aria-pressed="'+(i===0)+'">'+r.n+'</button>';}).join("")+'</div>'+
   '<div class="rolebox" id="rvbox" aria-live="polite"></div></section>'+
   '<section class="psec"><h2>Three sensors, three views</h2><p class="sub">Each story shows all three. They see different things, so we compare timing and direction, not numbers.</p><div class="sens3">'+
   '<div class="sc"><h3>NISAR <small>L-band radar</small></h3><p>Wavelength about 24 cm. Reaches deeper into vegetation, so it is good for flooded plants and ground moisture. Channels used: HH and HV. Provisional data, 12-day repeat.</p></div>'+
   '<div class="sc"><h3>Sentinel-1 <small>C-band radar</small></h3><p>Wavelength about 5.5 cm. Reflects more from the top of the canopy and goes dark over water easily. Channels used: VV and VH. More frequent dates; fills NISAR gaps.</p></div>'+
   '<div class="sc"><h3>Sentinel-2 <small>optical</small></h3><p>Measures sunlight, so colours look natural, but cloud blocks it. We use it as a picture of the ground, not for numbers.</p></div></div>'+
   '<p class="cap">NISAR and Sentinel-1 never passed at the same moment, and L-band and C-band numbers are never compared dB for dB.</p></section>'+
   '<div class="pnote"><b>Read with care.</b> One date pair per story, so these are the results in our seven test sites, not a general rule. Method: NISAR GCOV HHHH and HVHV, 9×9 smoothing, median alignment per pair, 3 dB threshold, share of valid pixels. "Consistent with" means the pattern fits an explanation, not that it proves it.</div></section>'+
   footer()+'</div>';
  drawPolSwitch(); drawMix();
  rvS.p="nw"; drawRv(); $$("[data-rvp]").forEach(function(b){b.onclick=function(){rvS.p=b.dataset.rvp;drawRv();};});
  $$("[data-pm]").forEach(function(b){b.onclick=function(){ps.mode=b.dataset.pm;$$("[data-pm]").forEach(function(x){x.setAttribute("aria-pressed",x===b);});$("#prows").innerHTML=polRows();};});
  if(hl&&$("#pr_"+hl)){setTimeout(function(){$("#pr_"+hl).scrollIntoView({block:"center"});},30);}else window.scrollTo(0,0);
}


/* ---------------- NEW TO RADAR? (plain-words guide) ---------------- */

var rd={i:0,v:"r"};
var RD=[
 {n:"Minneriya tank",r:"img/mn_nisar_jul02.webp",o:"img/mn_s2_jun25.webp",dr:"NISAR, 2 Jul 2026",dopt:"Sentinel-2, 25 Jun 2026",
  cr:"The tank is dark blue-black: calm water bounces the pulse away. Forest is yellow-green: leaves and branches scatter plenty back in HV. The purple patches fit open or less vegetated land.",
  co:"The same area as a camera sees it: the tank is dark water, and the forest is dark green. Compare where the shapes match."},
 {n:"Matara (cloud)",r:"img/mt_nisar_sep12.webp",o:"img/mt_s2_sep08.webp",dr:"NISAR, 12 Sep 2026",dopt:"Sentinel-2, 8 Sep 2026",
  cr:"The radar picture is clear: sea dark blue, land yellow-green, a pink-white patch near the coast, consistent with built-up land. The two pictures are four days apart.",
  co:"The ordinary satellite photo is mostly covered by cloud. This is why radar matters in the monsoon."},
 {n:"Colombo Port",r:"img/pt_nisar_jul14.webp",o:"img/pt_s2_jul08.webp",dr:"NISAR, 14 Jul 2026",dopt:"Sentinel-2, 8 Jul 2026",
  cr:"Container stacks and other hard structures are bright, because metal and walls scatter the pulse strongly. Calm harbour water and smooth ground are purple-blue and dark.",
  co:"The same port as a camera sees it. Compare where the container yards sit with the bright patches in the radar picture."}
];
function drawRd(){
  var r=RD[rd.i], isR=rd.v==="r";
  $("#rdImg").src=isR?r.r:r.o; $("#rdImg").alt=(isR?"NISAR radar image of ":"Sentinel-2 optical image of ")+r.n;
  $("#rdTag").textContent=isR?r.dr:r.dopt; $("#rdCap").textContent=isR?r.cr:r.co;
  $$("[data-rd]").forEach(function(b){b.setAttribute("aria-pressed",String(+b.dataset.rd===rd.i));});
  $$("[data-rv]").forEach(function(b){b.setAttribute("aria-pressed",String(b.dataset.rv===rd.v));});
}
function faqL(q,h){return '<details class="faq"><summary>'+q+'</summary><div class="faql">'+h+'</div></details>';}
function faq(q,a){return '<details class="faq"><summary>'+q+'</summary><p>'+a+'</p></details>';}

/* ---------------- RADAR IN 60 SECONDS (demo on #/radar) ---------------- */
var DM={k:"water"};
var DEMO={
 water:{n:"Smooth water",tile:"ex_sea",tn:"Dark",tcap:"Calm sea · Colombo Port, 14 Jul",bar:8,
  echo:"Very weak. Smooth water acts like a mirror, so the pulse bounces away from the satellite.",
  see:"You see: black to deep blue-violet.",lab:"almost nothing comes back"},
 forest:{n:"Forest",tile:"ex_veg",tn:"Green to yellow",tcap:"Vegetation or crops · Thailand, 30 Sep",bar:62,
  echo:"Medium to strong. Leaves and branches scatter the pulse in every direction, and some of it returns, especially in HV.",
  see:"You see: green to yellow.",lab:"a good share scatters back"},
 build:{n:"Building",tile:"ex_bld",tn:"Pink to white",tcap:"Container stacks · Colombo Port, 14 Jul",bar:96,
  echo:"Very strong. Hard walls and the ground form a corner that sends the pulse straight back (a double bounce).",
  see:"You see: pink to white.",lab:"most of it comes straight back"}
};
function demoScene(k){
  var pe=(k==="build")?108:176;
  var pulse='<g stroke="#8fd8ff" stroke-width="3" stroke-linecap="round" fill="none" class="dpulse"><path d="M270 78 L270 '+(pe-6)+'"/><path d="M300 78 L300 '+(pe-6)+'"/><path d="M330 78 L330 '+(pe-6)+'"/></g>'+
   '<g fill="#8fd8ff"><path d="M262 '+(pe-6)+' l8 12 l8 -12z"/><path d="M292 '+(pe-6)+' l8 12 l8 -12z"/><path d="M322 '+(pe-6)+' l8 12 l8 -12z"/></g>';
  var sat='<g><rect x="284" y="22" width="32" height="22" rx="4" fill="#e8eefc"/><rect x="246" y="28" width="32" height="10" rx="2" fill="#4a6fd8"/><rect x="322" y="28" width="32" height="10" rx="2" fill="#4a6fd8"/><path d="M300 44 L300 56" stroke="#e8eefc" stroke-width="3"/><text x="300" y="14" text-anchor="middle" fill="#9fb0d6" font-size="12">satellite</text></g>';
  var g="", e="";
  if(k==="water"){
    g='<rect x="60" y="190" width="480" height="60" fill="#18337a" opacity=".55"/><path d="M60 190 H540" stroke="#6f8fe8" stroke-width="3"/>';
    e='<g class="decho" stroke="#9fb0d6" stroke-width="3" stroke-linecap="round" fill="none" stroke-dasharray="3 7" opacity=".7"><path d="M340 186 L470 128"/></g><path d="M462 122 l14 -2 l-6 12z" fill="#9fb0d6" opacity=".7"/><text x="476" y="116" fill="#9fb0d6" font-size="12" text-anchor="middle">bounces away</text>';
  } else if(k==="forest"){
    var t="";for(var i=0;i<9;i++){var x=110+i*48;t+='<rect x="'+(x-3)+'" y="170" width="6" height="22" fill="#5a4a2a"/><circle cx="'+x+'" cy="158" r="'+(17+(i%3)*3)+'" fill="#2f7a2f"/>';}
    g='<rect x="60" y="190" width="480" height="60" fill="#2a2418"/>'+t;
    var eo="";[[210,150,170,100],[270,142,262,92],[330,142,342,92],[390,150,432,100],[300,140,300,86]].forEach(function(a){eo+='<path d="M'+a[0]+' '+a[1]+' L'+a[2]+' '+a[3]+'"/>';});
    e='<g class="decho" stroke="#b9e03e" stroke-width="3" stroke-linecap="round" fill="none" stroke-dasharray="3 7">'+eo+'</g><text x="300" y="76" fill="#b9e03e" font-size="12" text-anchor="middle" opacity="0">.</text><text x="470" y="108" fill="#b9e03e" font-size="12" text-anchor="middle">scatters back</text>';
  } else {
    g='<rect x="60" y="190" width="480" height="60" fill="#2a2d3a"/><rect x="250" y="120" width="100" height="70" fill="#8b93ad"/><rect x="262" y="132" width="14" height="14" fill="#3a4060"/><rect x="290" y="132" width="14" height="14" fill="#3a4060"/><rect x="318" y="132" width="14" height="14" fill="#3a4060"/>';
    e='<g class="decho" stroke="#f2bde8" stroke-width="6" stroke-linecap="round" fill="none" stroke-dasharray="4 9"><path d="M360 112 L360 70"/></g><path d="M350 74 l10 -14 l10 14z" fill="#f2bde8"/><text x="440" y="96" fill="#f2bde8" font-size="12" text-anchor="middle">straight back</text>';
  }
  return '<svg viewBox="0 0 600 260" role="img" aria-label="Diagram: radar pulse and echo over '+DEMO[k].n.toLowerCase()+'">'+g+sat+pulse+e+'</svg>';
}
function drawDemo(){
  var c=$("#rdemo"); if(!c)return;
  var d=DEMO[DM.k];
  c.innerHTML='<div class="dleft"><div class="seg" role="group" aria-label="Pick a surface">'+Object.keys(DEMO).map(function(k){return '<button type="button" data-dm="'+k+'" aria-pressed="'+(DM.k===k)+'">'+DEMO[k].n+'</button>';}).join("")+'</div>'+
   '<p class="dq">Echo strength</p><div class="dmeter" aria-hidden="true"><i style="width:'+d.bar+'%"></i></div><p class="dlab">'+esc(d.lab)+'</p>'+
   '<p class="dtx">'+esc(d.echo)+'</p>'+
   '<div class="dres"><img src="img/'+d.tile+'.webp" alt="Example of '+esc(d.tn.toLowerCase())+' in a NISAR picture"><div><b>'+esc(d.see)+'</b><span>'+esc(d.tcap)+'</span></div></div></div>'+
   '<div class="dscene">'+demoScene(DM.k)+'</div>';
  $$("[data-dm]",c).forEach(function(b){b.onclick=function(){DM.k=b.dataset.dm;drawDemo();};});
}
function renderRadar(){
  stopPlay(); document.body.classList.remove("site-open");
  app.innerHTML='<div class="site polar radar">'+
   '<div class="crumb"><a href="#/">Home</a> › <span>New to radar?</span></div>'+
   '<div class="shead"><div class="tag">Start here</div><h1>New to radar? Read this first</h1><div class="place">Everything in this app is made from radar pictures. This page explains, in plain words, what they are and how to read them. No background needed.</div></div>'+
   '<section class="psec"><h2>Radar in 60 seconds</h2><p class="sub">A satellite sends a pulse down and listens for the echo. Pick a surface and see how much comes back, and what colour it makes.</p><div class="rdemo" id="rdemo"></div></section>'+
   '<section class="psec"><h2>Basics you must know</h2><p class="sub">Click a card to open it.</p>'+
   '<div class="steps">'+
   '<details class="step"><summary onclick="var o=!this.parentNode.open;var d=this.parentNode.parentNode.children;for(var i=0;i<d.length;i++)d[i].open=o;return false;"><span class="sn">1 · Light</span><h3>Radar brings its own light</h3></summary><p class="sbody">It works day or night and through cloud and rain, so it can show a flood when a normal photo only shows grey cloud.</p></details>'+
   '<details class="step"><summary onclick="var o=!this.parentNode.open;var d=this.parentNode.parentNode.children;for(var i=0;i<d.length;i++)d[i].open=o;return false;"><span class="sn">2 · Echo</span><h3>Bright = strong echo, dark = weak echo</h3></summary><p class="sbody">Strength is in decibels (dB). In this app "dark" means below a stated threshold, and a "change" means darker than the reference by more than 3 dB.</p></details>'+
   '<details class="step"><summary onclick="var o=!this.parentNode.open;var d=this.parentNode.parentNode.children;for(var i=0;i<d.length;i++)d[i].open=o;return false;"><span class="sn">3 · Bands</span><h3>L-band reaches deeper than C-band</h3></summary><p class="sbody">NISAR (L-band, about 24 cm) slips between leaves; Sentinel-1 (C-band, about 5.5 cm) stays near the top; Sentinel-2 is an optical camera. We never compare their dB for dB.</p></details>'+
   '</div></section>'+
   '<section class="psec"><h2>1. HH and HV</h2><p class="sub">Polarization is the direction the wave wiggles, sent and received.</p>'+
   '<div class="pcards"><div class="pc hh"><h3><i></i>HH</h3><p>Sent horizontally, received horizontally. Responds to the ground surface and to "double bounces" off trunks, buildings and flooded plants.</p></div>'+
   '<div class="pc hv"><h3><i></i>HV</h3><p>Sent horizontally, received vertically. The twist happens inside leaves and branches, so HV follows vegetation.</p></div></div>'+
   '<p class="cap">The <a href="#/polar">Polarizations page</a> shows which one highlights which change, story by story. Every story also has a "Polarization used" row.</p></section>'+
   '<section class="psec"><h2>2. Same place, two views</h2><p class="sub">Radar has no real colour, so we assign one: red = HH, green = HV, blue = HH − HV. Pick a place and flip between the radar picture and an ordinary satellite photo to see what the colours mean.</p>'+
   '<div class="roles" role="group" aria-label="Choose a place" id="rdPlace">'+RD.map(function(r,i){return '<button type="button" data-rd="'+i+'" aria-pressed="'+(i===0)+'">'+r.n+'</button>';}).join("")+'</div>'+
   '<div class="rdbox"><div class="seg" role="group" aria-label="Choose a view"><button type="button" data-rv="r" aria-pressed="true">Radar (NISAR)</button><button type="button" data-rv="o" aria-pressed="false">Optical (Sentinel-2)</button></div>'+
   '<div class="rdimg"><img id="rdImg" alt=""><span id="rdTag" class="clab"></span></div><p class="rdcap" id="rdCap" aria-live="polite"></p></div>'+
   '<p class="cap">These are display colours, not the colour of the ground. More examples are on the <a href="#/polar">Polarizations page</a>.</p></section>'+
   '<section class="psec"><h2>Quick questions</h2>'+
   faqL("How do I read a story?",'<ol class="tl"><li><b>Start with the question</b> at the top of the story. Each one asks something a person could ask.</li><li><b>Use the before/after slider.</b> Drag it and watch what turns dark, bright or changes colour.</li><li><b>Check the dates.</b> Every image is labelled with its sensor and date. Provisional data can still change.</li><li><b>Read the time series.</b> The line shows the change over weeks, with rain bars underneath so you can see what the weather was doing.</li><li><b>Read the limits.</b> Every story says what radar cannot tell us.</li></ol>')+
   faq("What does \"consistent with\" mean?","The picture fits the explanation and the other evidence does not contradict it. It is weaker than \"proves\". Radar shows what changed on the surface; the cause comes from rain data, news reports or other satellites.")+
   faq("Why is the data called provisional?","NISAR began releasing data in 2026 and early products are checked later. Validated products replace provisional ones, so numbers may shift slightly. We use validated data where we could, and say which is which.")+
   faq("Is dark always water?","No. Smooth bare ground, sand, tarmac and radar shadow behind steep hills are also dark. We check with a second sensor, the dates and the rain before calling something water.")+
   faq("Why does the same place look different on different dates?","Wet soil, growing crops, wind on water and the time of day all change the echo. That change is what the stories are looking at.")+
   faq("Can I compare NISAR and Sentinel-1 numbers?","Only the pattern, not the numbers. They use different wavelengths and pass at different times.")+
   faq("Where does the data come from?","NISAR from NASA-ISRO via the ASF DAAC, Sentinel-1 and Sentinel-2 from Copernicus, rain from NASA GPM IMERG and NASA POWER. The full list is in the credits at the bottom of every page.")+
   '</section>'+
   '<div class="pnote"><b>Ready?</b> <a href="#stories">Pick a story</a>, open the <a href="#/polar">Polarizations page</a>, or see the <a href="#/moisture">Rain test</a>.</div>'+
   footer()+'</div>';
  DM.k="water";drawDemo(); rd.i=0;rd.v="r";drawRd(); $$("[data-rd]").forEach(function(b){b.onclick=function(){rd.i=+b.dataset.rd;drawRd();};}); $$("[data-rv]").forEach(function(b){b.onclick=function(){rd.v=b.dataset.rv;drawRd();};});
  window.scrollTo(0,0);
}

/* ---------------- MOISTURE: can radar feel the rain? (Nawalapitiya) ---------------- */
var PLACES={nw:window.NAW,am:window.AMP,rn:window.RAT}, NAW=PLACES.nw, nw={tr:"a",i:0,ctrl:"hv"}, NWC={W:900,H:644,L:68,R:12};
function nwP(){return NAW.tracks[nw.tr].pts;}
function nwImg(tr,p){return "img/"+(NAW.pre||"nw_")+tr+"_"+p.d.replace(/-/g,"")+".webp";}
function nwAdd(d,n){return new Date((dnum(d)+n)*864e5).toISOString().slice(0,10);}
function nwMean(a){var s=0;a.forEach(function(x){s+=x;});return s/a.length;}
function nwPf(p){return p<0.01?p.toFixed(3):p.toFixed(2);}
function nwSgn(x,dp){return (x>=0?"+":"−")+Math.abs(x).toFixed(dp);}
var nwX=function(d){var D0=dnum("2026-06-10"),D1=dnum("2026-11-14");return NWC.L+(dnum(d)-D0)/(D1-D0)*(NWC.W-NWC.L-NWC.R);};
function nwMonths(top,bot,lab){
  var o="";
  [["2026-07-01","Jul"],["2026-08-01","Aug"],["2026-09-01","Sep"],["2026-10-01","Oct"],["2026-11-01","Nov"]].forEach(function(m){
    o+='<line x1="'+nwX(m[0])+'" x2="'+nwX(m[0])+'" y1="'+top+'" y2="'+bot+'" stroke="#1a2745"/><text x="'+(nwX(m[0])+4)+'" y="'+lab+'">'+m[1]+'</text>';});
  return o;
}
function nwChart(){
  var P=nwP(), cur=P[nw.i], W=NWC.W, L=NWC.L, R=NWC.R;
  var YR=NAW.tracks[nw.tr].yr||[140,172,[140,150,160,170]], VL=NAW.tracks[nw.tr].vl||NAW.vlabel||['provisional','validated, offset-corrected'];
  var gT=16,gB=250,rT=292,rB=592,glo=YR[0],ghi=YR[1],rhi=(NAW.rhi||80);
  var yg=function(v){return gB-(v-glo)/(ghi-glo)*(gB-gT);}, yr=function(v){return rB-v/rhi*(rB-rT);};
  var o='<svg class="chart" viewBox="0 0 '+W+' '+NWC.H+'" role="img" aria-label="Green intensity of NISAR radar images and daily rainfall, June to November 2026">';
  o+='<rect x="'+nwX(NAW.gap[0])+'" y="'+gT+'" width="'+(nwX(NAW.gap[1])-nwX(NAW.gap[0]))+'" height="'+(rB-gT)+'" fill="#18223d"/><text x="'+(nwX(NAW.gap[0])+4)+'" y="'+(gT+12)+'" style="font-size:10px">no NISAR data</text>';
  o+='<rect x="'+nwX(nwAdd(cur.d,-7))+'" y="'+gT+'" width="'+(nwX(cur.d)-nwX(nwAdd(cur.d,-7)))+'" height="'+(rB-gT)+'" fill="rgba(76,201,240,.14)"/>';
  YR[2].forEach(function(v){o+='<line x1="'+L+'" x2="'+(W-R)+'" y1="'+yg(v)+'" y2="'+yg(v)+'" stroke="#243357"/><text x="'+(L-6)+'" y="'+(yg(v)+4)+'" text-anchor="end">'+v+'</text>';});
  [0,rhi/2,rhi].forEach(function(v){o+='<line x1="'+L+'" x2="'+(W-R)+'" y1="'+yr(v)+'" y2="'+yr(v)+'" stroke="#243357"/><text x="'+(L-6)+'" y="'+(yr(v)+4)+'" text-anchor="end">'+v+'</text>';});
  o+=nwMonths(gT,rB,rB+16);
  o+='<text x="'+(L+6)+'" y="'+(gB-6)+'" style="font-size:11px;fill:#7bd88f">green intensity of the green pixels (0–255)</text>';
  o+='<text x="'+(L+6)+'" y="'+(rT+12)+'" style="font-size:11px">rain per day, mm (IMERG)</text>';
  var bw=Math.max(1.5,(W-L-R)/(dnum("2026-11-14")-dnum("2026-06-10"))*0.78), w0=nwAdd(cur.d,-7);
  Object.keys(NAW.rain).forEach(function(d){
    var v=NAW.rain[d], inw=(d>=w0&&d<cur.d);
    o+='<rect x="'+(nwX(d)-bw/2).toFixed(1)+'" y="'+yr(v).toFixed(1)+'" width="'+bw.toFixed(1)+'" height="'+(rB-yr(v)).toFixed(1)+'" fill="'+(inw?"#4cc9f0":"#6f8fc4")+'"/>';});
  o+='<polyline fill="none" stroke="#2DB800" stroke-width="2.4" points="'+P.map(function(p){return nwX(p.d).toFixed(1)+","+yg(p.g).toFixed(1);}).join(" ")+'"/>';
  o+='<line x1="'+nwX(cur.d)+'" x2="'+nwX(cur.d)+'" y1="'+gT+'" y2="'+rB+'" stroke="#fff" stroke-dasharray="4 4" stroke-width="1.2"/>';
  P.forEach(function(p,i){
    var x=nwX(p.d).toFixed(1), y=yg(p.g).toFixed(1), on=(i===nw.i);
    o+='<g class="pt" data-i="'+i+'" tabindex="0" role="button" aria-label="'+fmtIso(p.d)+', green intensity '+p.g.toFixed(1)+', rain in the 7 days before '+Math.round(p.rain7)+' mm">'+
      '<circle cx="'+x+'" cy="'+y+'" r="14" fill="transparent"/>'+
      (on?'<circle cx="'+x+'" cy="'+y+'" r="10" fill="none" stroke="#fff" stroke-width="2"/>':"")+
      '<circle cx="'+x+'" cy="'+y+'" r="'+(on?6.5:5)+'" fill="'+(p.v?"#0b1224":"#2DB800")+'" stroke="#2DB800" stroke-width="2.5"/>'+
      '<title>'+fmtIso(p.d)+': green intensity '+p.g.toFixed(1)+', rain in the 7 days before '+Math.round(p.rain7)+' mm'+(p.v?" ("+VL[1]+")":"")+'</title></g>';});
  o+='<text x="'+Math.min(nwX(cur.d)+8,W-R-70)+'" y="'+(yg(cur.g)-14).toFixed(1)+'" style="fill:#fff;font-size:12px;font-weight:700">'+cur.g.toFixed(1)+'</text>';
  o+=ytitle(15,(gT+gB)/2,'Green intensity (0–255)')+ytitle(15,(rT+rB)/2,'Rain (mm per day)')+xtitle((L+W-R)/2,rB+36,'Date, 2026');
  return o+'</svg>';
}
function nwCtrl(){
  var P=nwP(), hv=(nw.ctrl==="hv"), f=hv?"fhv":"fhh", n=hv?"nhv":"nhh", col=hv?"#2DB800":"#E5484D";
  var prov=P.filter(function(p){return !p.v;});
  var mf=nwMean(prov.map(function(p){return p[f];})), mn=nwMean(prov.map(function(p){return p[n];}));
  var F=P.map(function(p){return p[f]-mf;}), N=P.map(function(p){return p[n]-mn;});
  var all=F.concat(N), lo=Math.floor(Math.min.apply(null,all)*4)/4, hi=Math.ceil(Math.max.apply(null,all)*4)/4;
  var W=NWC.W, L=NWC.L, R=NWC.R, T=14, B=250, y=function(v){return B-(v-lo)/(hi-lo)*(B-T);};
  var o='<svg class="chart" viewBox="0 0 '+W+' 300" role="img" aria-label="Change in '+(hv?"HV":"HH")+' backscatter over forest and over open land">';
  o+='<rect x="'+nwX(NAW.gap[0])+'" y="'+T+'" width="'+(nwX(NAW.gap[1])-nwX(NAW.gap[0]))+'" height="'+(B-T)+'" fill="#18223d"/>';
  for(var v=lo;v<=hi+1e-9;v+=0.25){o+='<line x1="'+L+'" x2="'+(W-R)+'" y1="'+y(v)+'" y2="'+y(v)+'" stroke="'+(Math.abs(v)<1e-9?"#5b6d96":"#243357")+'"/><text x="'+(L-6)+'" y="'+(y(v)+4)+'" text-anchor="end">'+(v>0?"+":"")+v.toFixed(2)+'</text>';}
  o+=nwMonths(T,B,B+16);
  o+='<text x="'+(L+6)+'" y="'+(T+12)+'" style="font-size:11px">change in '+(hv?"HV":"HH")+' from the provisional average (dB)</text>';
  o+='<line x1="'+nwX(P[nw.i].d)+'" x2="'+nwX(P[nw.i].d)+'" y1="'+T+'" y2="'+B+'" stroke="#fff" stroke-dasharray="4 4" stroke-width="1.2"/>';
  o+='<polyline fill="none" stroke="'+col+'" stroke-width="2.6" points="'+P.map(function(p,i){return nwX(p.d).toFixed(1)+","+y(F[i]).toFixed(1);}).join(" ")+'"/>';
  o+='<polyline fill="none" stroke="'+col+'" stroke-opacity=".75" stroke-width="2.4" stroke-dasharray="7 5" points="'+P.map(function(p,i){return nwX(p.d).toFixed(1)+","+y(N[i]).toFixed(1);}).join(" ")+'"/>';
  P.forEach(function(p,i){
    var x=nwX(p.d).toFixed(1), fill=p.v?"#0b1224":col;
    o+='<circle cx="'+x+'" cy="'+y(F[i]).toFixed(1)+'" r="4.5" fill="'+fill+'" stroke="'+col+'" stroke-width="2"><title>'+fmtIso(p.d)+', forest '+nwSgn(F[i],2)+' dB</title></circle>'+
       '<rect x="'+(x-4.5)+'" y="'+(y(N[i])-4.5).toFixed(1)+'" width="9" height="9" fill="'+fill+'" stroke="'+col+'" stroke-width="2"><title>'+fmtIso(p.d)+', open land '+nwSgn(N[i],2)+' dB</title></rect>';});
  o+=ytitle(15,(T+B)/2,'Change in '+(hv?'HV':'HH')+' (dB)')+xtitle((L+W-R)/2,B+36,'Date, 2026');
  return o+'</svg>';
}
function nwCaption(){
  var p=nwP()[nw.i], T=NAW.tracks[nw.tr], VL=T.vl||NAW.vlabel||['provisional','validated, offset-corrected'];
  return '<b>'+fmtIso(p.d)+' 2026</b> · '+(p.v?VL[1]:VL[0])+' · '+T.name.toLowerCase()+' ('+T.dir+', '+T.time+')<br>'+
   'Rain in the 7 days before: <b>'+Math.round(p.rain7)+' mm</b> · green intensity: <b>'+p.g.toFixed(1)+'</b>'+(T.nopct?'':' · green pixels: '+p.pct.toFixed(1)+'% of the scene');
}
function nwShow(){
  var p=nwP()[nw.i], im=$("#nwimg"); if(!im)return;
  im.src=nwImg(nw.tr,p); im.alt="Green pixels only, NISAR "+T0()+" pass, "+fmtIso(p.d);
  function T0(){return NAW.tracks[nw.tr].name.toLowerCase();}
  $("#nwcap").innerHTML=nwCaption();
  var r=$("#nwr"); r.max=nwP().length-1; r.value=nw.i; $("#nwdate").textContent=fmtIso(p.d);
  var c=$("#nwchart"); c.innerHTML=nwChart();
  $$(".pt",c).forEach(function(g){var go=function(){stopPlay();nw.i=+g.dataset.i;nwShow();};g.onclick=go;g.onkeydown=function(e){if(e.key==="Enter"||e.key===" "){e.preventDefault();go();}};});
  if($("#nwctrl"))$("#nwctrl").innerHTML=nwCtrl();
}
function nwStatsTable(){
  var a=NAW.stats.a, d=NAW.stats.d, O=NAW.offsets;
  var rows=[
   ["Dates compared with rain",a.g.n,d.g.n],
   ["Green intensity vs rain in the previous 7 days: correlation r",a.g.r.toFixed(2),d.g.r.toFixed(2)],
   ["Chance of a pattern this strong from random dates (p)",nwPf(a.g.p),nwPf(d.g.p)],
   ["Same, provisional dates only (r)",a.g.rprov.toFixed(2),d.g.rprov.toFixed(2)],
   ["Green intensity change per +100 mm of rain (0–255 scale)",nwSgn(a.g.slope,1),nwSgn(d.g.slope,1)],
   ["HV change per +100 mm, forest",nwSgn(a.fhv.slope,2)+" dB",nwSgn(d.fhv.slope,2)+" dB"],
   ["HV change per +100 mm, open land",nwSgn(a.nhv.slope,2)+" dB",nwSgn(d.nhv.slope,2)+" dB"],
   ["HH change per +100 mm, forest / open land",nwSgn(a.fhh.slope,2)+" / "+nwSgn(a.nhh.slope,2)+" dB",nwSgn(d.fhh.slope,2)+" / "+nwSgn(d.nhh.slope,2)+" dB"],
   ["HH of the red pixels vs AMSR2 soil moisture (r)",a.soil.hh_sm.r.toFixed(2)+" (p "+nwPf(a.soil.hh_sm.p)+")",d.soil.hh_sm.r.toFixed(2)+" (p "+nwPf(d.soil.hh_sm.p)+"; 5 dates with 2–3 AMSR2 observations: "+d.soil.hh_sm2.r.toFixed(2)+")"],
   ["HV of the green pixels vs AMSR2 soil moisture (r)",a.soil.hv_sm.r.toFixed(2)+" (p "+nwPf(a.soil.hv_sm.p)+")",d.soil.hv_sm.r.toFixed(2)+" (p "+nwPf(d.soil.hv_sm.p)+")"],
   ["HH of the red pixels vs rain in the previous 7 days (r)",a.soil.hh7.r.toFixed(2)+" (p "+nwPf(a.soil.hh7.p)+")",d.soil.hh7.r.toFixed(2)+" (p "+nwPf(d.soil.hh7.p)+")"],
   ["Added to validated dates (HH / HV)",nwSgn(O.a.HH,2)+" / "+nwSgn(O.a.HV,2)+" dB",nwSgn(O.d.HH,2)+" / "+nwSgn(O.d.HV,2)+" dB"]];
  return '<table class="nwt"><thead><tr><th></th><th>Morning pass<br><small>ascending</small></th><th>Evening pass<br><small>descending</small></th></tr></thead><tbody>'+
    rows.map(function(r){return '<tr><td>'+esc(r[0])+'</td><td>'+esc(r[1])+'</td><td>'+esc(r[2])+'</td></tr>';}).join("")+'</tbody></table>';
}
function nwBody(){
  var a=NAW.stats.a, d=NAW.stats.d;
  var tabsNW=tabsShell([
   ["tk","Key takeaway",'<h2 class="tkone">Over Nawalapitiya, NISAR’s green (HV) signal rose after wet weeks and fell after dry ones. The morning pass shows it clearly, and the evening pass points the same way. Open tea land and grassland responded about twice as strongly as forest, which fits a radar that feels moisture in soil and low plants.</h2>'+
    '<div class="tkgrid"><div><h3>For scientists and officials</h3><p>L-band radar follows rainfall without needing clear skies. Over hill country where cloud is common, this is a first check that NISAR could help track soil wetness. It is a test of the idea, not a service.</p></div>'+
    '<div><h3>For farmers and communities</h3><p>One day a radar picture could show how wet slopes and tea estates have been over recent weeks. Here we only show that the signal follows rain; we do not turn it into advice.</p></div>'+
    '<div class="care"><h3>Handle with care</h3><p>One area, 12 morning and 7 evening dates. The morning result is significant (p about '+nwPf(a.g.p)+'). The evening result is not on all 7 dates (r = '+d.g.r.toFixed(2)+', p about '+nwPf(d.g.p)+'); on the 6 provisional dates it is r = '+d.g.rprov.toFixed(2)+' (p about '+nwPf(d.g.pprov)+'). Radar also responds to plant water and roughness, and rain is a coarse 10 km estimate.</p></div></div>'],
   ["see","What we see",'<ul>'+
    '<li>Both passes show the same rise and fall: lowest after the dry weeks of mid and late July, higher after the August rains, highest after the heavy rain of late September and mid-October.</li>'+
    '<li>Morning pass: 12 Sep dipped after a drier week (about 35 mm) and 24 Sep peaked after about 172 mm.</li>'+
    '<li>The share of green pixels is about 44–45% in June–July, 46–48% in August–September and 50–52% in early and mid October (morning pass). On the validated dates it reads higher still (57–59%); that share depends on a fixed threshold that the processing step shifts, so we do not read that jump as ground change.</li>'+
    '<li>The evening pass, 18:34 local, shows the same pattern, so morning dew alone does not explain it.</li>'+
    '<li>HH and HV rise together with rain on forest and on non-forest (r about 0.6–0.75, both passes). HV − HH changes by only about 0.2–0.3 dB, so the two polarisations respond alike here and do not separate wetting from vegetation change. The one nominally significant case (morning pass, non-forest, p about 0.01) amounts to 0.3 dB, within the processing offsets of 0.1–0.7 dB, so we do not read it as a finding.</li>'+
    '<li>After the validated step is corrected, 30 Oct, 11 Nov and 27 Oct continue the October level.</li></ul>'],
   ["prov","Provisional vs validated",'<div class="two"><div class="box"><h3>What changed on 21 October</h3><p>NISAR products moved from PROVISIONAL to VALIDATED. On forest, which does not change, validated images read lower in HH by '+NAW.offsets.a.HH.toFixed(2)+' dB (morning pass) and '+NAW.offsets.d.HH.toFixed(2)+' dB (evening pass), and slightly lower in HV. That is a processing difference, not the ground. We added the forest-measured offset to the validated dates (hollow markers), after which they continue the October trend.</p></div>'+
    '<div class="box"><h3>Why this is not circular</h3><p>The offset was measured on forest, so forest lines up by design. The independent test is the correlation using provisional dates only: r = '+a.g.rprov.toFixed(2)+' (morning) and '+d.g.rprov.toFixed(2)+' (evening), about the same as with all dates. All other stories use provisional data only, so none of them is affected.</p></div></div>'],
   ["num","The numbers",nwStatsTable()],
   ["data","Data used",'<table>'+
    '<tr><td>NISAR GCOV, L-band</td><td>Track 084 ascending, frame 005, 12 dates (10 provisional, 2 validated), 20 Jun – 11 Nov. Track 048 descending, frame 085, 7 dates (6 provisional, 1 validated), 17 Jun – 27 Oct. HH and HV, 10 m.</td></tr>'+
    '<tr><td>Green and red pixels</td><td>One fixed colour stretch (R = HH, G = HV, B = HH − HV). Green pixels are HV-strong (leaves and stems), red pixels are those where HH is clearly stronger than HV (bare and open ground, roads, buildings); everything else is white. Means are taken in linear power, then converted to dB where dB is shown. The pixel sets are counted separately on each date.</td></tr>'+
    '<tr><td>Rain</td><td>NASA GPM IMERG Late daily (GPM_3IMERGDL v07), area mean, via GES DISC Giovanni.</td></tr><tr><td>Soil moisture</td><td>AMSR2 (LPRM, 6.9 GHz, 10 km grid) daily area mean for the same box, via Giovanni. Each NISAR pass is matched to the mean of the day before, the pass day and the day after, because AMSR2 has many empty days.</td></tr>'+
    '<tr><td>Forest</td><td>ESA WorldCover 2021 v200, 10 m; pixels checked against the map and Google Earth.</td></tr></table>'],
   ["lim","Limits",'<ul>'+
    '<li>Correlation, not proof of cause. Radar also responds to plant water and surface roughness, and each track has its own viewing angle.</li>'+
    '<li>Morning pass: 12 dates, p about '+nwPf(a.g.p)+'. Evening pass: 7 dates, r = '+d.g.r.toFixed(2)+', p about '+nwPf(d.g.p)+', not significant; on the 6 provisional dates r = '+d.g.rprov.toFixed(2)+' (p about '+nwPf(d.g.pprov)+'). Treat the evening pass as suggestive at most.</li>'+
    '<li>Rain is a satellite estimate (GPM IMERG, about 10 km) averaged over the box. Soils also remember older rain, and irrigation is not included.</li>'+
    '<li>The response flattens in late October and November, when soils were probably already saturated after a very wet month.</li>'+
    '<li>“Green intensity” is a display value from a fixed colour stretch; the table gives physical dB values for HV and HH. For the validated dates the forest-measured HV offset was added in dB and converted to display units (about '+NAW.k_units_per_dB.toFixed(1)+' per dB, from the provisional dates of both passes).</li><li>AMSR2 soil moisture is a coarse microwave estimate of the top few centimetres. Each 3-day mean uses 1 to 2 observations, and none is valid within a day of 19 August. Soil moisture is compared with HH of the red pixels, whose pixel set is counted separately on each date.</li>'+
    '<li>“Open land” is everything that is not forest. WorldCover often labels tea as grassland.</li>'+
    '<li>No NISAR data exist between 27 July and 10 August 2026.</li></ul>'],
   ["why","Why it may happen",'<p class="whyp">Water raises how strongly a surface reflects radar. After rain, wet soil and wet plants send more L-band energy back, so HV (leaves and stems) and HH (soil and trunks) both rise. Published L-band studies, for example El Hajj et al. 2019 (Remote Sensing 11:31) and Ayari et al. 2022 (Sensors 22:580), report the same direction of response.</p>'],
   ["loc","Where is this?",locBody("nw")]
  ],true);
  return '<div class="shead pl"><div class="tag">Hill country, wet zone · Central Province</div><h2>Nawalapitiya</h2>'+
  '<div class="place">Hill country of the Central Province, 80.45–80.62°E, 6.90–7.10°N (about 19 × 22 km): forest, tea estates and a small town. 19 NISAR passes, 17 June to 11 November 2026.</div>'+mapBtn("nw")+'</div>'+
  '<div class="stats">'+
   '<div class="stat"><b>r = '+a.g.r.toFixed(2)+' · '+d.g.r.toFixed(2)+'</b><span>green intensity vs rain in the 7 days before each pass (morning · evening)</span></div>'+
   '<div class="stat"><b>218–219 → 229–231</b><span>green intensity, driest passes (16–21 mm in the week before) → wettest (125–172 mm)</span></div>'+
   '<div class="stat"><b>about 2×</b><span>open land vs forest response in HV: '+nwSgn(a.nhv.slope,2)+' vs '+nwSgn(a.fhv.slope,2)+' dB per +100 mm (morning)</span></div>'+
   '<div class="stat"><b>0.3–0.7 dB</b><span>step between provisional and validated products, measured on forest and corrected</span></div></div>'+
  '<div class="nwsec"><h2>Watch the green change with the rain</h2><p class="sub">Only the green pixels are kept (strong HV: leaves and stems); everything else is white. Press play, drag the slider or click a point on the graph.</p>'+
   '<div class="ctl"><div class="seg" role="group" aria-label="Pass"><button data-ntr="a" aria-pressed="'+(nw.tr==="a")+'">Morning pass · ascending</button><button data-ntr="d" aria-pressed="'+(nw.tr==="d")+'">Evening pass · descending</button></div>'+
   '<button class="btn" id="play" aria-pressed="false">▶ Time-lapse</button><label>Date <input type="range" id="nwr" min="0" max="11" value="0" aria-label="Date"> <b id="nwdate"></b></label></div>'+
   '<div class="nwgrid"><div class="nwleft">'+
    '<figure class="nwfr"><div class="nwimgbox"><img id="nwimg" src="" alt=""></div><figcaption id="nwcap"></figcaption></figure></div>'+
    '<div class="nwright"><div class="chartbox nwcb"><div class="in"><h3>Green intensity and rain</h3><p class="cap">Green line: how bright the green pixels are (0–255, one fixed stretch for all dates). Bars: rain per day. The blue bars are the 7 days before the pass shown.</p><div id="nwchart"></div>'+
    '<div class="legendrow"><span><i class="dot"></i>provisional</span><span><i class="dot hol"></i>validated, offset-corrected</span><span><i class="bar"></i>rain in the 7 days before the pass</span></div></div></div></div></div></div>'+
  '<div class="nwsec"><h2>Is it moisture, or is the land changing?</h2><p class="sub">Forest does not change in a few months. We marked forest with ESA WorldCover (98–99% tree cover) and compared it with everything else: tea, grass, fields and town. Both move together, open land moves more.</p>'+
   '<div class="chartbox nwcb"><div class="in"><div class="ctl" style="margin-bottom:6px"><div class="seg" role="group" aria-label="Channel"><button data-nc="hv" aria-pressed="'+(nw.ctrl==="hv")+'" class="bhv">HV (green)</button><button data-nc="hh" aria-pressed="'+(nw.ctrl==="hh")+'" class="bhh">HH (red)</button></div></div>'+
   '<div id="nwctrl"></div><div class="legendrow"><span><i class="ln"></i>forest (circles)</span><span><i class="ln dash"></i>open land: tea, grass, fields, town (squares)</span></div></div></div>'+
   '<p class="cap" style="margin-top:8px">Both groups rise and fall on the same dates, so the change is not land clearing or construction. In open land the radar reaches soil and low plants; the dense forest canopy already scatters strongly, so its response is smaller. Each track is compared only with itself.</p></div>'+
  amSecond()+
  tabsNW;
}
function wireNw(){
  ["a","d"].forEach(function(t){NAW.tracks[t].pts.forEach(function(p){var im=new Image();im.src=nwImg(t,p);});});
  $$("[data-ntr]").forEach(function(b){b.onclick=function(){
    stopPlay(); var d0=nwP()[nw.i].d; nw.tr=b.dataset.ntr;
    var P=nwP(),best=0,bd=1e9; P.forEach(function(p,i){var x=Math.abs(dnum(p.d)-dnum(d0));if(x<bd){bd=x;best=i;}});
    nw.i=best; $$("[data-ntr]").forEach(function(x){x.setAttribute("aria-pressed",x===b);}); nwShow();};});
  $$("[data-nc]").forEach(function(b){b.onclick=function(){nw.ctrl=b.dataset.nc;$$("[data-nc]").forEach(function(x){x.setAttribute("aria-pressed",x===b);});$("#nwctrl").innerHTML=nwCtrl();};});
  $("#nwr").oninput=function(){stopPlay();nw.i=+this.value;nwShow();};
  $("#play").onclick=function(){
    if(timer){stopPlay();return;}
    var b=$("#play"); b.setAttribute("aria-pressed","true"); b.textContent="❚❚ Pause";
    timer=setInterval(function(){nw.i=(nw.i+1)%nwP().length;nwShow();},1000);};
  wireTabs(); nwShow();
}
/* ---------------- Ampara body (second place of the Rain test) ---------------- */
var amh={tr:"d",i:0}, amTimer=null;
function amStop(){if(amTimer){clearInterval(amTimer);amTimer=null;}var b=$("#amplay");if(b){b.setAttribute("aria-pressed","false");b.textContent="▶ Time-lapse";}}
function amPts(){var P=NAW.tracks[amh.tr].pts;return P.filter(function(p){return !p.noH;});}
function amHs(d){return NAW.hs[amh.tr].filter(function(h){return h.d===d;})[0];}
function amShow(){
  var im=$("#amimg"); if(!im)return; var p=amPts()[amh.i], T=NAW.tracks[amh.tr], e=amHs(p.d), pre=(NAW.pre||"nw_");
  im.src="img/"+pre+"h"+amh.tr+"_"+p.d.replace(/-/g,"")+".webp"; im.alt="HH-dominant red and pink pixels only, NISAR "+T.name.toLowerCase()+", "+fmtIso(p.d);
  var isAm=(NAW===PLACES.am), isRn=(NAW===PLACES.rn), mode=isRn?(amh.tr==='d'?(p.v?' · quad-pol mode':' · dual-pol'):''):isAm?(amh.tr==="d"?' · '+(p.v?"quad-pol mode, 20 m":"dual-pol, 10 m"):''):(p.v?' · validated product, offset added':' · provisional');
  $("#amcap").innerHTML='<b>'+fmtIso(p.d)+' 2026</b> · '+T.name.toLowerCase()+' ('+T.dir+', '+T.time+')'+mode+'<br>HH of the '+NAW.hslab[amh.tr]+': <b>'+e.hh.toFixed(2)+' dB</b> · AMSR2 soil moisture: <b>'+(e.sm==null?'no observation within a day':e.sm.toFixed(1)+' %')+'</b> · rain on the pass day: '+e.rain1.toFixed(1)+' mm'+(NAW.hsnote[amh.tr]?'<br>'+NAW.hsnote[amh.tr]:'');
  var r=$("#amr"); r.max=amPts().length-1; r.value=amh.i; $("#amdate").textContent=fmtIso(p.d);
  $("#amsoil").innerHTML=amSoilChart(p.d,amh.tr);
  var so=isRn?NAW.st[amh.tr].hh_sm:isAm?(amh.tr==="a"?NAW.stats.asoil.hh_sm:null):NAW.stats[amh.tr].soil.hh_sm;
  $("#amcapt").textContent=(amh.tr==="d"?"Evening pass":"Morning pass")+(so?": HH of the red pixels in dB against AMSR2 soil moisture r = "+so.r.toFixed(2)+" (p "+nwPf(so.p)+")"+(so.p<0.05?"":", not significant")+((isAm||isRn)?"":"; validated dates have the forest offset added")+". ":". ")+"The dashed line follows the date shown in the picture.";
}
function amSoilChart(cur,tr){
  var A=NAW, P=A.hs[tr], W=NWC.W, L=NWC.L, R=NWC.R, Y=A.hsy[tr];
  var pan=[
   {t:14,b:132,lo:Y.hh[0],hi:Y.hh[1],tk:Y.hh[2],lab:"NISAR HH of the "+A.hslab[tr]+" (dB)",f:function(p){return p.hh;},col:"#E5484D",fm:function(v){return v.toFixed(2)+" dB";}},
   {t:170,b:288,lo:Y.sm[0],hi:Y.sm[1],tk:Y.sm[2],lab:"AMSR2 soil moisture (%)",f:function(p){return p.sm;},col:"#4cc9f0",fm:function(v){return v.toFixed(1)+" %";}}];
  var rT=326,rB=640,rhi=A.rhi||50, yr=function(v){return rB-v/rhi*(rB-rT);};
  var o='<svg class="chart" viewBox="0 0 '+W+' 694" role="img" aria-label="NISAR HH signal, AMSR2 soil moisture and daily rain, June to November 2026">';
  o+='<rect x="'+nwX(A.gap[0])+'" y="14" width="'+(nwX(A.gap[1])-nwX(A.gap[0]))+'" height="'+(rB-14)+'" fill="#18223d"/><text x="'+(nwX(A.gap[0])+4)+'" y="26" style="font-size:10px">no NISAR data</text>';
  pan.forEach(function(q){
    var y=function(v){return q.b-(v-q.lo)/(q.hi-q.lo)*(q.b-q.t);};
    var Q=P.filter(function(p){return q.f(p)!=null;});
    q.tk.forEach(function(v){o+='<line x1="'+L+'" x2="'+(W-R)+'" y1="'+y(v)+'" y2="'+y(v)+'" stroke="#243357"/><text x="'+(L-6)+'" y="'+(y(v)+4)+'" text-anchor="end">'+(q.lo<0?v.toFixed(1):v)+'</text>';});
    o+='<text x="'+(L+6)+'" y="'+(q.t+12)+'" style="font-size:11px;fill:'+q.col+'">'+q.lab+'</text>';
    o+='<polyline fill="none" stroke="'+q.col+'" stroke-width="2.4" points="'+Q.map(function(p){return nwX(p.d).toFixed(1)+","+y(q.f(p)).toFixed(1);}).join(" ")+'"/>';
    Q.forEach(function(p){o+='<circle cx="'+nwX(p.d).toFixed(1)+'" cy="'+y(q.f(p)).toFixed(1)+'" r="5" fill="'+(p.v?"#0b1224":q.col)+'" stroke="'+q.col+'" stroke-width="2.5"><title>'+fmtIso(p.d)+': '+q.fm(q.f(p))+(p.v?A.vtag:"")+'</title></circle>';});
  });
  [0,rhi/2,rhi].forEach(function(v){o+='<line x1="'+L+'" x2="'+(W-R)+'" y1="'+yr(v)+'" y2="'+yr(v)+'" stroke="#243357"/><text x="'+(L-6)+'" y="'+(yr(v)+4)+'" text-anchor="end">'+v+'</text>';});
  o+='<text x="'+(L+6)+'" y="'+(rT+12)+'" style="font-size:11px">rain per day, mm (IMERG)</text>';
  var bw=Math.max(1.5,(W-L-R)/(dnum("2026-11-14")-dnum("2026-06-10"))*0.78);
  Object.keys(A.rain).forEach(function(d){var v=A.rain[d];o+='<rect x="'+(nwX(d)-bw/2).toFixed(1)+'" y="'+yr(Math.min(v,rhi)).toFixed(1)+'" width="'+bw.toFixed(1)+'" height="'+(rB-yr(Math.min(v,rhi))).toFixed(1)+'" fill="#6f8fc4"/>';});
  o+=nwMonths(14,rB,rB+16);
  o+=ytitle(15,(pan[0].t+pan[0].b)/2,'HH (dB)')+ytitle(15,(pan[1].t+pan[1].b)/2,'Soil moisture (%)')+ytitle(15,(rT+rB)/2,'Rain (mm per day)')+xtitle((L+W-R)/2,rB+38,'Date, 2026');
  if(cur)o+='<line x1="'+nwX(cur)+'" x2="'+nwX(cur)+'" y1="14" y2="'+rB+'" stroke="#fff" stroke-dasharray="4 4" stroke-width="1.2"/>';
  return o+'</svg>';
}
function amStatsTable(){
  var A=PLACES.am, a=A.stats.a, d=A.stats.d, so=A.stats.soil, as=A.stats.asoil, nr="not run";
  var rows=[
   ["Dates compared with rain",a.g.n,d.g.n],
   ["Green intensity vs rain in the previous 7 days: correlation r",a.g.r.toFixed(2),d.g.r.toFixed(2)],
   ["Chance of a pattern this strong from random dates (p)",nwPf(a.g.p),nwPf(d.g.p)],
   ["Same, dual-pol dates only (r)","all 10 dates are dual-pol",d.gdual.r.toFixed(2)+" (5 dates, p "+nwPf(d.gdual.p)+")"],
   ["Green intensity change per +100 mm of rain (0–255 scale)",nwSgn(a.g.slope,1),nwSgn(d.g.slope,1)],
   ["HV of the green pixels, change per +100 mm",nwSgn(a.hv.slope,2)+" dB",nwSgn(d.hv.slope,2)+" dB"],
   ["HH of the red pixels vs rain in the previous 7 days (r)",a.hhfix.r.toFixed(2)+" (dB, p "+nwPf(a.hhfix.p)+")",d.hh7.r.toFixed(2)+" (p "+nwPf(d.hh7.p)+")"],
   ["HH vs rain on the pass day (r)",as.hh_rain1.r.toFixed(2)+" (p "+nwPf(as.hh_rain1.p)+")",so.hh_rain1.r.toFixed(2)+" (dual-pol only: "+so.hh_rain1_dual.r.toFixed(2)+")"],
   ["HH vs AMSR2 soil moisture (r)",as.hh_sm.r.toFixed(2)+", p "+nwPf(as.hh_sm.p)+" (dates with 2–3 AMSR2 obs, 7 dates: "+as.hh_sm2.r.toFixed(2)+")",so.hh_sm.r.toFixed(2)+", p "+nwPf(so.hh_sm.p)+" (dual-pol only: "+so.hh_sm_dual.r.toFixed(2)+")"],
   ["HV vs AMSR2 soil moisture (r)",as.hv_sm.r.toFixed(2)+" (HV of the green pixels, p "+nwPf(as.hv_sm.p)+"; 7 dates: "+as.hv_sm2.r.toFixed(2)+")","whole box: "+so.hv_sm.r.toFixed(2)+" (dual-pol only: "+so.hv_sm_dual.r.toFixed(2)+")"],
   ["Change from the driest pass (16 Jul) to the wettest (20 Oct)","not run","HH +1.79 dB · HV of green pixels +1.26 dB"]];
  return '<table class="nwt"><thead><tr><th></th><th>Morning pass<br><small>ascending</small></th><th>Evening pass<br><small>descending, track 120</small></th></tr></thead><tbody>'+
    rows.map(function(r){return '<tr><td>'+esc(r[0])+'</td><td>'+esc(r[1])+'</td><td>'+esc(r[2])+'</td></tr>';}).join("")+'</tbody></table>'+
    '<p class="cap" style="margin-top:8px">“not run” means we did not run that test for the morning pass. Soil moisture is the same daily AMSR2 series for both passes. The morning HH uses the red pixels of each date, not a fixed set.</p>';
}
function amSecond(){
  var isAm=(NAW===PLACES.am), isRn=(NAW===PLACES.rn), L2=NAW.leg2;
  var sub=isRn?'Rain is a coarse estimate, so we also compared the HH (red) signal of both passes with AMSR2 soil moisture, a different satellite and sensor. Only the red and pink HH-dominant pixels are shown (bare and open ground, roads and buildings); everything else is white. The pixel set is counted separately on each date. Press play, drag the slider or switch the pass.':isAm?'Rain is a coarse estimate, so we also compared the HH (red) signal of both passes with AMSR2 soil moisture, a different satellite and sensor. On the evening pass we kept a fixed set of 575,000 HH-dominant pixels (fallow paddy, bare soil, roads, buildings) so the same ground is measured on every date; the morning pass uses the HH-dominant pixels of each date. Only the red and pink HH-dominant pixels are shown; everything else is white. Press play, drag the slider or switch the pass.':
   'Rain is a coarse estimate, so we also compared the HH (red) signal of both passes with AMSR2 soil moisture, a different satellite and sensor. Only the red and pink HH-dominant pixels are shown (bare and open ground, roads and buildings); everything else is white. The pixel set is counted separately on each date. Press play, drag the slider or switch the pass.';
  var foot=isRn?'HH and soil moisture rise and fall together on the evening pass, and more weakly on the morning pass. We read this as consistent with wetting of the ground, not proof of it. The four quad-pol evening dates are hollow markers. Soil moisture is a coarse 10 km estimate, and the morning pass of 19 August has no valid observation within a day.':isAm?'HH, soil moisture and rain rise together from the dry July to the wet October. That supports reading the change as wetting of the ground, not land-cover change. The evening pass shows it more clearly than the morning pass.':
   'HH, soil moisture and rain broadly rise together from the dry July to the wet October, with the clearest link on the evening pass dates that have 2–3 AMSR2 observations. We read it as consistent with wetting of the ground. Soil moisture is a coarse 10 km estimate with no valid observation within a day of 19 August.';
  var dual=NAW.tracks.a.pts.filter(function(p){return !p.noH;}).length;
  var b1=isAm?'<button data-ahr="d" aria-pressed="true">Evening pass · descending</button><button data-ahr="a" aria-pressed="false">Morning pass · ascending</button>':'<button data-ahr="d" aria-pressed="true">Evening pass · descending</button><button data-ahr="a" aria-pressed="false">Morning pass · ascending</button>';
  return '<div class="nwsec"><h2>A second check: is it soil moisture?</h2><p class="sub">'+sub+'</p>'+
   '<div class="ctl"><div class="seg" role="group" aria-label="Pass">'+b1+'</div>'+
   '<button class="btn" id="amplay" aria-pressed="false">▶ Time-lapse</button><label>Date <input type="range" id="amr" min="0" max="8" value="0" aria-label="Date"> <b id="amdate"></b></label></div>'+
   '<div class="nwgrid"><div class="nwleft"><figure class="nwfr"><div class="nwimgbox"><img id="amimg" src="" alt=""></div><figcaption id="amcap"></figcaption></figure></div>'+
    '<div class="nwright"><div class="chartbox nwcb"><div class="in"><h3>HH, soil moisture and rain</h3><p class="cap" id="amcapt"></p><div id="amsoil"></div>'+
    '<div class="legendrow"><span><i class="dot" style="background:#E5484D;border-color:#E5484D"></i>'+L2[0]+'</span><span><i class="dot hol" style="border-color:#E5484D"></i>'+L2[1]+'</span><span><i class="bar"></i>rain per day</span></div></div></div></div></div>'+
   '<p class="cap" style="margin-top:8px">'+foot+'</p></div>';
}
function amBody(){
  var A=PLACES.am, a=A.stats.a, d=A.stats.d, so=A.stats.soil, A0=A.stats.asoil;
  var tabs=tabsShell([
   ["tk","Key takeaway",'<h2 class="tkone">Over Ampara, NISAR’s green (HV) signal tended to be higher after wetter weeks, and on the evening pass the HH signal followed independent soil moisture. The pattern is weaker and less certain than at Nawalapitiya.</h2>'+
    '<div class="tkgrid"><div><h3>For scientists and officials</h3><p>A drier place is a harder test. If the same response appears in hill country and in the dry zone, it is more likely to be moisture than local land cover. It is a test of the idea, not a service.</p></div>'+
    '<div><h3>For farmers and communities</h3><p>Paddy and scrub in the dry zone depend on seasonal rain and tank water. One day a radar picture could show how wet the ground has been. Here we only show that the signal follows rain and soil moisture; we do not turn it into advice.</p></div>'+
    '<div class="care"><h3>Handle with care</h3><p>Ten morning and nine evening dates. Both results are suggestive, not conclusive: morning r = '+a.g.r.toFixed(2)+' (p about '+nwPf(a.g.p)+'), evening r = '+d.g.r.toFixed(2)+' (p about '+nwPf(d.g.p)+'). Four evening dates are in a different radar mode.</p></div></div>'],
   ["see","What we see",'<ul>'+
    '<li>Evening pass: green intensity is lowest on 4 and 16 July, after about 1.5 mm of rain in the week before, and highest on 20 October, after about 55 mm.</li>'+
    '<li>HH of the fixed red (HH-dominant) pixels rose by 1.79 dB from the driest date (16 July) to the wettest (20 October). HV of the green pixels rose by 1.26 dB over the same dates. These are different pixel sets, so the two numbers are not a like-for-like comparison and we do not read a difference between them.</li>'+
    '<li>Both channels move together. HV − HH changes by only about 0.1–0.4 dB across the season and does not follow rain significantly, so at Ampara the two polarisations respond alike and we cannot separate wetting from vegetation change by polarisation.</li>'+
    '<li>HH and AMSR2 soil moisture rise and fall on the same dates. In September, all three quad-pol dates agree: down on 2 September, up on 14 September, down on 26 September. The mode is the same on those dates, so the mode change cannot explain that swing. Both then rise on 8 October (dual-pol). HH is highest on 20 October and soil moisture on 8 October.</li>'+
    '<li>Morning pass (track 156): the same direction. Green intensity is lowest on 7 and 19 July, after about 0–1 mm of rain in the week before, and highest on 23 October, after about 79 mm. 12 August is also high after only about 7 mm, which keeps r at '+a.g.r.toFixed(2)+'.</li>'+
    '<li>Morning pass and soil moisture: HH of the red pixels and AMSR2 soil moisture both rise toward October but not date by date (r = '+A0.hh_sm.r.toFixed(2)+', p '+nwPf(A0.hh_sm.p)+'; '+A0.hh_sm2.r.toFixed(2)+' on the 7 dates with 2–3 AMSR2 observations). That is suggestive, and weaker than the evening pass.</li>'+
    '<li>The outlier on the evening pass is 21 August: HH is high while soil moisture is average, which fits an offset from the change to quad-pol mode.</li></ul>'],
   ["mode","Radar mode",'<div class="two"><div class="box"><h3>Four evening dates are quad-pol</h3><p>On 21 August and on 2, 14 and 26 September the radar recorded all four polarisations (quad-pol, 20 m) instead of the usual HH and HV (dual-pol, 10 m). They are shown as hollow markers. The share of pixels that count as green is lower on those dates (35–39% against 43–55%), so we do not compare green pixel counts across modes.</p></div>'+
    '<div class="box"><h3>How we handled it</h3><p>At Nawalapitiya we could measure and remove a processing offset on forest. Here there are too few dates in each mode to do that, so we did not correct anything. Instead we report the result with and without the quad-pol dates: green vs rain r = '+d.g.r.toFixed(2)+' with all dates and '+d.gdual.r.toFixed(2)+' with the five dual-pol dates; HH vs soil moisture r = '+so.hh_sm.r.toFixed(2)+' and '+so.hh_sm_dual.r.toFixed(2)+'. Five dates is very few, so read both as suggestive.</p></div></div>'],
   ["num","The numbers",amStatsTable()],
   ["data","Data used",'<table>'+
    '<tr><td>NISAR GCOV, L-band</td><td>Morning pass (ascending, track 156): 10 dates, 25 Jun – 23 Oct 2026, all dual-pol (HH and HV), 10 m grid, provisional. Evening pass (descending, track 120): 9 dates, 22 Jun – 20 Oct 2026, provisional; 5 dual-pol dates (HH, HV) and 4 quad-pol dates (21 Aug – 26 Sep, 20 m), shown on a 20 m grid.</td></tr>'+
    '<tr><td>Green pixels</td><td>HV-strong pixels (leaves and stems), kept on a fixed colour stretch (R = HH, G = HV, B = HH − HV); everything else is white. Means are taken in linear power, then converted to dB where dB is shown.</td></tr>'+
    '<tr><td>Red (HH) pixels</td><td>Pixels where red is clearly stronger than green (R − G ≥ 9, R ≥ 64): fallow paddy, bare soil, roads and buildings. We kept a fixed set of 575,000 pixels that are HH-dominant on at least half of the nine evening dates, so the same ground is measured each time. HH is read in dB from the dB files, with water below −18 dB left out. On the morning pass the red pixels are counted separately on each date (1.2–1.7 million pixels), so that pixel set is not fixed.</td></tr>'+
    '<tr><td>Rain</td><td>NASA GPM IMERG Early daily (GPM_3IMERGDE v07), mean over the box, via GES DISC Giovanni.</td></tr>'+
    '<tr><td>Soil moisture</td><td>AMSR2 (LPRM, 6.9 GHz, night pass, 10 km grid) for the same box, via Giovanni. Each NISAR pass is matched to the mean of the day before, the pass day and the day after, because AMSR2 has many empty days.</td></tr></table>'],
   ["lim","Limits",'<ul>'+
    '<li>Correlation, not proof of cause. Radar also responds to plant water and roughness, and each track has its own viewing angle, so each track is compared only with itself.</li>'+
    '<li>Few dates: 10 morning and 9 evening. The evening result is suggestive (p about '+nwPf(d.g.p)+'); the morning result is also suggestive, not conclusive (p about '+nwPf(a.g.p)+').</li>'+
    '<li>Four evening dates are in quad-pol mode and may carry an offset we could not measure. On the five dual-pol dates the correlations are higher, but five dates is a very small sample.</li>'+
    '<li>Rain is a satellite estimate (IMERG Early, about 10 km), a quick version that is less refined than later runs. Rain “on the pass day” is a UTC day total, so part of it falls after the pass. Soil memory and irrigation (paddy fields and tanks) are not included.</li>'+
    '<li>AMSR2 soil moisture is a coarse microwave estimate of the top few centimetres and is the same daily series for both passes. Each 3-day mean uses only 1 to 3 AMSR2 observations (evening pass: just 1 on 4 Jul, 21 Aug and 8 Oct; morning pass: just 1 on 25 Jun, 12 Aug and 29 Sep).</li>'+
    '<li>The box includes part of the Senanayake Samudraya reservoir, whose water level changes through the season. Open water is not green, and for HH we left out water below −18 dB, but the green pixel set still changes a little from date to date. The evening-pass HH test uses a fixed pixel set to avoid this.</li>'+
    '<li>We did not split forest from open land at Ampara, as we did at Nawalapitiya.</li>'+
    '<li>No NISAR data exist between 27 July and 10 August 2026.</li></ul>'],
   ["why","Why it may happen",'<p class="whyp">Water raises how strongly a surface reflects radar. After rain, wet soil and wet plants send more L-band energy back. In the dry zone the ground is more open, so HH, which responds to bare and fallow soil, can react directly to wetting, while HV (leaves and stems) responds more weakly. Published L-band studies, for example El Hajj et al. 2019 (Remote Sensing 11:31) and Ayari et al. 2022 (Sensors 22:580), report the same direction of response.</p>'],
   ["loc","Where is this?",locBody("am")]
  ],true);
  return '<div class="shead pl"><div class="tag">Dry zone · Ampara district, Eastern Province</div><h2>Ampara</h2>'+
  '<div class="place">East of the island, 81.45–81.70°E, 7.10–7.35°N (about 28 × 28 km): dry-zone forest and scrub, paddy land and the Senanayake Samudraya reservoir. 19 NISAR passes, 22 June to 23 October 2026.</div>'+mapBtn("am")+'</div>'+
  '<div class="stats">'+
   '<div class="stat"><b>r = '+a.g.r.toFixed(2)+' · '+d.g.r.toFixed(2)+'</b><span>green intensity vs rain in the 7 days before each pass (morning · evening)</span></div>'+
   '<div class="stat"><b>p ≈ '+nwPf(a.g.p)+' · '+nwPf(d.g.p)+'</b><span>chance of a pattern this strong from random dates (morning · evening). Not conclusive.</span></div>'+
   '<div class="stat"><b>+1.79 dB</b><span>HH of the same ground, driest pass (16 Jul) to wettest (20 Oct), evening pass</span></div>'+
   '<div class="stat"><b>r = '+so.hh_sm.r.toFixed(2)+'</b><span>HH vs AMSR2 soil moisture, 9 evening passes ('+so.hh_sm_dual.r.toFixed(2)+' on the 5 dual-pol dates). Morning pass: r = '+A.stats.asoil.hh_sm.r.toFixed(2)+', 10 dates.</span></div></div>'+
  '<div class="nwsec"><h2>Watch the green change with the rain</h2><p class="sub">Only the green pixels are kept (strong HV: leaves and stems); everything else is white. Press play, drag the slider or click a point on the graph.</p>'+
   '<div class="ctl"><div class="seg" role="group" aria-label="Pass"><button data-ntr="a" aria-pressed="true">Morning pass · ascending</button><button data-ntr="d" aria-pressed="false">Evening pass · descending</button></div>'+
   '<button class="btn" id="play" aria-pressed="false">▶ Time-lapse</button><label>Date <input type="range" id="nwr" min="0" max="9" value="0" aria-label="Date"> <b id="nwdate"></b></label></div>'+
   '<div class="nwgrid"><div class="nwleft"><figure class="nwfr"><div class="nwimgbox"><img id="nwimg" src="" alt=""></div><figcaption id="nwcap"></figcaption></figure></div>'+
    '<div class="nwright"><div class="chartbox nwcb"><div class="in"><h3>Green intensity and rain</h3><p class="cap">Green line: how bright the green pixels are (0–255, one fixed stretch for all dates; the two passes use different vertical scales). Bars: rain per day. The blue bars are the 7 days before the pass shown.</p><div id="nwchart"></div>'+
    '<div class="legendrow"><span><i class="dot"></i>dual-pol or provisional</span><span><i class="dot hol"></i>quad-pol mode, 20 m (evening pass)</span><span><i class="bar"></i>rain in the 7 days before the pass</span></div></div></div></div></div></div>'+
  amSecond()+
  tabs;
}
/* ---------------- Ratnapura body (third place of the Rain test) ---------------- */
function rnStatsTable(){
  var R=PLACES.rn, a=R.st.a, d=R.st.d, dd=R.st.dd;
  var rows=[
   ["Dates compared with rain",a.g.n,d.g.n],
   ["Green intensity vs rain in the previous 7 days: correlation r",a.g.r.toFixed(2),d.g.r.toFixed(2)],
   ["Chance of a pattern this strong from random dates (p)",nwPf(a.g.p),nwPf(d.g.p)],
   ["Same, dual-pol dates only (r)","all 10 dates are dual-pol",dd.g.r.toFixed(2)+" ("+dd.g.n+" dates, p "+nwPf(dd.g.p)+")"],
   ["Green intensity change per +100 mm of rain (0–255 scale)",nwSgn(a.g.slope,1),nwSgn(d.g.slope,1)+" (dual-pol only: "+nwSgn(dd.g.slope,1)+")"],
   ["HV of the green pixels, change per +100 mm",nwSgn(a.hv.slope,2)+" dB",nwSgn(d.hv.slope,2)+" dB"],
   ["HH of the red pixels vs rain in the previous 7 days (r)",a.hh7.r.toFixed(2)+" (p "+nwPf(a.hh7.p)+")",d.hh7.r.toFixed(2)+" (p "+nwPf(d.hh7.p)+"; dual-pol only: "+dd.hh7.r.toFixed(2)+")"],
   ["HH vs rain on the pass day (r)",a.hh_rain1.r.toFixed(2)+" (p "+nwPf(a.hh_rain1.p)+")",d.hh_rain1.r.toFixed(2)+" (p "+nwPf(d.hh_rain1.p)+"; dual-pol only: "+dd.hh_rain1.r.toFixed(2)+")"],
   ["HH vs AMSR2 soil moisture (r)",a.hh_sm.r.toFixed(2)+", p "+nwPf(a.hh_sm.p)+" ("+a.hh_sm.n+" dates; "+a.hh_sm2.n+" dates with 2–3 AMSR2 obs: "+a.hh_sm2.r.toFixed(2)+")",d.hh_sm.r.toFixed(2)+", p "+nwPf(d.hh_sm.p)+" (dual-pol only: "+dd.hh_sm.r.toFixed(2)+"; "+d.hh_sm2.n+" dates with 2–3 obs: "+d.hh_sm2.r.toFixed(2)+", p "+nwPf(d.hh_sm2.p)+")"],
   ["HV of the green pixels vs AMSR2 soil moisture (r)",a.hv_sm.r.toFixed(2)+" (p "+nwPf(a.hv_sm.p)+")",d.hv_sm.r.toFixed(2)+" (p "+nwPf(d.hv_sm.p)+"; dual-pol only: "+dd.hv_sm.r.toFixed(2)+")"],
   ["Change from the driest pass to the wettest dual-pol pass","14 Jul → 24 Sep: HH +0.88 dB · HV of green pixels +0.79 dB","11 Jul → 15 Oct: HH +1.19 dB · HV of green pixels +0.93 dB"]];
  return '<table class="nwt"><thead><tr><th></th><th>Morning pass<br><small>ascending, track 084</small></th><th>Evening pass<br><small>descending, track 048</small></th></tr></thead><tbody>'+
    rows.map(function(r){return '<tr><td>'+esc(r[0])+'</td><td>'+esc(String(r[1]))+'</td><td>'+esc(String(r[2]))+'</td></tr>';}).join("")+'</tbody></table>'+
    '<p class="cap" style="margin-top:8px">Soil moisture is the same daily AMSR2 series for both passes. On both passes the red pixels are counted separately on each date, so that pixel set is not fixed. Validated products (from 21 October) are not included.</p>';
}
function rnBody(){
  var R=PLACES.rn, a=R.st.a, d=R.st.d, dd=R.st.dd;
  var tabs=tabsShell([
   ["tk","Key takeaway",'<h2 class="tkone">Over Ratnapura, NISAR’s green (HV) signal rose after wet weeks and fell after dry ones, on both passes: r = '+a.g.r.toFixed(2)+' on 10 morning dates and r = '+d.g.r.toFixed(2)+' on 10 evening dates. On the evening pass, HH also followed independent satellite soil moisture (r = '+d.hh_sm.r.toFixed(2)+').</h2>'+
    '<div class="tkgrid"><div><h3>For scientists and officials</h3><p>A third place, with its own rainfall and ground, gives the idea another test. The same response appeared at Nawalapitiya, so it is less likely to be a local accident. It is a test of the idea, not a service.</p></div>'+
    '<div><h3>For farmers and communities</h3><p>One day a radar picture could show how wet the ground has been over recent weeks, even under cloud. Here we only show that the signal follows rain and soil moisture; we do not turn it into advice.</p></div>'+
    '<div class="care"><h3>Handle with care</h3><p>Ten morning and ten evening dates, provisional data. Morning p about '+nwPf(a.g.p)+', evening p about '+nwPf(d.g.p)+'. Four evening dates are in a different radar mode; on the six dual-pol dates r = '+dd.g.r.toFixed(2)+' (p about '+nwPf(dd.g.p)+'), a very small sample. Rain is a coarse estimate, and no landslide or flood data were checked.</p></div></div>'],
   ["see","What we see",'<ul>'+
    '<li>Morning pass: green intensity is lowest on 14 July (224.0), after about 10 mm of rain in the week before, and highest on 24 September (234.1), after about 179 mm. 18 October also followed about 179 mm and is high (231.8).</li>'+
    '<li>Evening pass: green intensity is lowest on 23 July (222.5, after about 29 mm; 11 July, after about 15 mm, is also low at 224.5) and highest on 15 October (236.6), after about 169 mm.</li>'+
    '<li>HH of the red pixels rose by 0.88 dB on the morning pass from the driest date (14 July) to the wettest (24 September), and HV of the green pixels by 0.79 dB. These are different pixel sets, so the two numbers are not a like-for-like comparison and we do not read a difference between them.</li>'+
    '<li>Not every date follows the rain: the 2 July morning pass comes after about 102 mm but is lower than 20 June, which came after about 63 mm.</li>'+
    '<li>HH and AMSR2 soil moisture rise and fall together on the evening pass: r = '+d.hh_sm.r.toFixed(2)+' on 10 dates (p '+nwPf(d.hh_sm.p)+'), and '+d.hh_sm2.r.toFixed(2)+' on the 7 dates with 2–3 AMSR2 observations. On the morning pass it is weaker and borderline (r = '+a.hh_sm.r.toFixed(2)+', p '+nwPf(a.hh_sm.p)+').</li>'+
    '<li>HH and HV rise together with rain. We cannot separate wetting from vegetation change by polarisation here.</li></ul>'],
   ["mode","Radar mode",'<div class="two"><div class="box"><h3>Four evening dates look quad-pol</h3><p>On 28 August and on 9 and 21 September and 3 October the evening images change character: fewer green pixels (about 650,000–690,000 against 760,000–820,000) and a larger red share (19–22% against 11–15%). NISAR’s scene list for track 048 shows quad-pol (QPDH) products on exactly these four dates. They are shown as hollow markers. We did not compare pixel counts across modes.</p></div>'+
    '<div class="box"><h3>How we handled it</h3><p>At Nawalapitiya we could measure and remove a processing offset on forest. Here there are too few dates in each mode, so we corrected nothing. Instead we report the result with and without the quad-pol dates: green vs rain r = '+d.g.r.toFixed(2)+' with all ten dates and '+dd.g.r.toFixed(2)+' with the six dual-pol dates; HH vs soil moisture r = '+d.hh_sm.r.toFixed(2)+' and '+dd.hh_sm.r.toFixed(2)+'. Six dates is very few, so read both as suggestive.</p></div></div>'],
   ["num","The numbers",rnStatsTable()],
   ["data","Data used",'<table>'+
    '<tr><td>NISAR GCOV, L-band</td><td>Morning pass (ascending, track 084): 10 dates, 20 Jun – 18 Oct 2026, dual-pol (HH and HV). Evening pass (descending, track 048): 10 dates, 17 Jun – 15 Oct 2026; 6 dual-pol dates and 4 quad-pol dates (28 Aug – 3 Oct). All provisional (CRID P05023). Three validated passes (30 Oct and 11 Nov morning, 27 Oct evening) are left out.</td></tr>'+
    '<tr><td>Green pixels</td><td>HV-strong pixels (leaves and stems), kept on a fixed colour stretch (R = HH, G = HV, B = HH − HV); everything else is white. Green intensity is the mean value of the green pixels on a 0–255 scale.</td></tr>'+
    '<tr><td>Red (HH) pixels</td><td>Pixels where HH clearly dominates (red and pink in the colour recipe): bare and open ground, roads and buildings. The set is counted separately on each date.</td></tr>'+
    '<tr><td>Rain</td><td>NASA GPM IMERG Late daily (GPM_3IMERGDL v07), mean over 80.28–80.55°E, 6.60–6.80°N (the data cell used was 80.35–80.45°E, 6.65–6.75°N), via GES DISC Giovanni.</td></tr>'+
    '<tr><td>Soil moisture</td><td>AMSR2 (LPRM, 6.9 GHz, 10 km grid) for the same box, via Giovanni. Each NISAR pass is matched to the mean of the day before, the pass day and the day after, because AMSR2 has many empty days.</td></tr></table>'],
   ["lim","Limits",'<ul>'+
    '<li>Correlation, not proof of cause. Radar also responds to plant water and roughness, and each track has its own viewing angle, so each track is compared only with itself.</li>'+
    '<li>Few dates: 10 morning and 10 evening. Both p values are below 0.05, but four evening dates are in quad-pol mode and may carry an offset we could not measure. On the six dual-pol dates the correlations are higher, but six dates is a very small sample.</li>'+
    '<li>Validated products (CRID P05036, from 21 October) are left out. At Nawalapitiya we measured a step of 0.3–0.7 dB between provisional and validated products on forest and corrected for it. We did not measure it here, so we did not mix the two.</li>'+
    '<li>Rain is a satellite estimate (IMERG Late, about 10 km). Rain “on the pass day” is a UTC day total, so part of it falls after the pass. Soil memory and irrigation are not included.</li>'+
    '<li>AMSR2 soil moisture is a coarse microwave estimate of the top few centimetres. Each 3-day mean uses 1 to 3 observations, except the morning pass of 19 August, which has none within a day and is left out of the soil moisture tests.</li>'+
    '<li>We did not split forest from open land at Ratnapura, and we did not characterise the land cover in the box.</li>'+
    '<li>No landslide, flood or field data were checked against these results.</li>'+
    '<li>No NISAR data exist between 27 July and 10 August 2026.</li></ul>'],
   ["why","Why it may happen",'<p class="whyp">Water raises how strongly a surface reflects radar. After rain, wet soil and wet plants send more L-band energy back. That is consistent with what we see here, but we did not separate soil from plants, so we do not claim which one drives it.</p>'],
   ["loc","Where is this?",locBody("rn")]
  ],true);
  return '<div class="shead pl"><div class="tag">Wet zone · Ratnapura district, Sabaragamuwa Province</div><h2>Ratnapura</h2>'+
  '<div class="place">South-west of the island, 80.28–80.55°E, 6.60–6.80°N (about 30 × 22 km), around Ratnapura town. 20 NISAR passes, 17 June to 18 October 2026.</div>'+mapBtn("rn")+'</div>'+
  '<div class="stats">'+
   '<div class="stat"><b>r = '+a.g.r.toFixed(2)+' · '+d.g.r.toFixed(2)+'</b><span>green intensity vs rain in the 7 days before each pass (morning · evening)</span></div>'+
   '<div class="stat"><b>p ≈ '+nwPf(a.g.p)+' · '+nwPf(d.g.p)+'</b><span>chance of a pattern this strong from random dates (morning · evening)</span></div>'+
   '<div class="stat"><b>+0.88 dB</b><span>HH of the red pixels, driest (14 Jul) to wettest (24 Sep) week, morning pass</span></div>'+
   '<div class="stat"><b>r = '+d.hh_sm.r.toFixed(2)+'</b><span>HH vs AMSR2 soil moisture, 10 evening passes ('+dd.hh_sm.r.toFixed(2)+' on the 6 dual-pol dates). Morning pass: r = '+a.hh_sm.r.toFixed(2)+', 9 dates.</span></div></div>'+
  '<div class="nwsec"><h2>Watch the green change with the rain</h2><p class="sub">Only the green pixels are kept (strong HV: leaves and stems); everything else is white. Press play, drag the slider or click a point on the graph.</p>'+
   '<div class="ctl"><div class="seg" role="group" aria-label="Pass"><button data-ntr="a" aria-pressed="true">Morning pass · ascending</button><button data-ntr="d" aria-pressed="false">Evening pass · descending</button></div>'+
   '<button class="btn" id="play" aria-pressed="false">▶ Time-lapse</button><label>Date <input type="range" id="nwr" min="0" max="9" value="0" aria-label="Date"> <b id="nwdate"></b></label></div>'+
   '<div class="nwgrid"><div class="nwleft"><figure class="nwfr"><div class="nwimgbox"><img id="nwimg" src="" alt=""></div><figcaption id="nwcap"></figcaption></figure></div>'+
    '<div class="nwright"><div class="chartbox nwcb"><div class="in"><h3>Green intensity and rain</h3><p class="cap">Green line: how bright the green pixels are (0–255, one fixed stretch for all dates; the two passes use different vertical scales). Bars: rain per day. The blue bars are the 7 days before the pass shown.</p><div id="nwchart"></div>'+
    '<div class="legendrow"><span><i class="dot"></i>dual-pol</span><span><i class="dot hol"></i>quad-pol mode (evening pass)</span><span><i class="bar"></i>rain in the 7 days before the pass</span></div></div></div></div></div></div>'+
  amSecond()+
  tabs;
}
function renderMoisture(place){
  stopPlay(); amStop(); document.body.classList.remove("site-open");
  place=(place==="am"||place==="ampara")?"am":(place==="rn"||place==="ratnapura")?"rn":"nw";
  app.innerHTML='<div class="site nw">'+
  '<div class="crumb"><a href="#/">Home</a> › <span>Rain test</span></div>'+
  '<div class="shead"><div class="tag">Validation test · Sri Lanka</div><h1>Can radar feel the rain?</h1></div>'+
  '<div class="headline"><p>Every other story here reads dark and bright patches as water, ground and plants. This one tests the colours: if NISAR really senses moisture, its signal should rise and fall with the rain where no flood or construction happens. We test it in three places: wet hill country, the dry-zone east and the south-west wet zone.</p></div>'+
  '<div class="placebar" role="tablist" aria-label="Test area">'+
   '<button role="tab" data-pl="nw" aria-selected="false"><b>Nawalapitiya</b><span>hill country · wet zone</span></button>'+
   '<button role="tab" data-pl="am" aria-selected="false"><b>Ampara</b><span>east · dry zone</span></button>'+
   '<button role="tab" data-pl="rn" aria-selected="false"><b>Ratnapura</b><span>south-west · wet zone</span></button></div>'+
  '<div id="mxplace" role="tabpanel"></div>'+
  '<div class="nextrow"><a class="btn" href="#/" style="text-decoration:none">← All stories</a><a class="btn" href="#/polar" style="text-decoration:none">HH and HV explained →</a></div>'+
  footer()+'</div>';
  $$("[data-pl]").forEach(function(b){b.onclick=function(){
    var pl=b.dataset.pl; if(b.getAttribute("aria-selected")==="true")return;
    try{history.replaceState(null,"","#/moisture"+(pl==="am"?"/ampara":pl==="rn"?"/ratnapura":""));}catch(e){}
    showPlace(pl);};});
  showPlace(place); window.scrollTo(0,0);
}
function wireAm(){
  var all=[];["a","d"].forEach(function(t){NAW.tracks[t].pts.forEach(function(p){if(p.noH)return;var im=new Image();im.src="img/"+(NAW.pre||"nw_")+"h"+t+"_"+p.d.replace(/-/g,"")+".webp";all.push(im);});});
  $$("[data-ahr]").forEach(function(b){b.onclick=function(){amStop();var d0=amPts()[amh.i].d;amh.tr=b.dataset.ahr;var P=amPts(),best=0,bd=1e9;P.forEach(function(p,i){var x=Math.abs(dnum(p.d)-dnum(d0));if(x<bd){bd=x;best=i;}});amh.i=best;$$("[data-ahr]").forEach(function(x){x.setAttribute("aria-pressed",x===b);});amShow();};});
  $("#amr").oninput=function(){amStop();amh.i=+this.value;amShow();};
  $("#amplay").onclick=function(){if(amTimer){amStop();return;}var b=$("#amplay");b.setAttribute("aria-pressed","true");b.textContent="❚❚ Pause";amTimer=setInterval(function(){if(!$("#amimg")){amStop();return;}amh.i=(amh.i+1)%amPts().length;amShow();},1000);};
  amShow();
}
function showPlace(place){
  stopPlay(); amStop(); NAW=PLACES[place]; nw={tr:"a",i:0,ctrl:"hv"}; amh={tr:"d",i:0};
  $$("[data-pl]").forEach(function(b){b.setAttribute("aria-selected",b.dataset.pl===place);});
  $("#mxplace").innerHTML=(place==="am"?amBody():place==="rn"?rnBody():nwBody());
  wireNw(); wireAm();
}


/* ---------------- routing, presenter ---------------- */
function route(){
  var h=location.hash||"#/", m=h.match(/^#\/site\/(\w+)/), pm=h.match(/^#\/polar(?:\/(\w+))?/), mm=h.match(/^#\/moisture(?:\/(\w+))?/);
  if(h==="#/radar")renderRadar(); else if(mm)renderMoisture(mm[1]); else if(pm)renderPolar(pm[1]); else if(m)renderSite(m[1]); else if(/^#(stories|colours|about|next)$/.test(h)){var e=document.getElementById(h.slice(1)); if(e)e.scrollIntoView();} else renderHome();
}
window.addEventListener("hashchange",function(e){
  var h=location.hash;
  if(/^#(stories|colours|about|next)$/.test(h)){
    if(!$("#stories")){location.hash="#/";setTimeout(function(){var el=document.getElementById(h.slice(1));if(el)el.scrollIntoView();},50);return;}
    var el=document.getElementById(h.slice(1)); if(el)el.scrollIntoView(); return;}
  route();
});
document.addEventListener("keydown",function(e){
  if(e.target.tagName==="SELECT"||e.target.tagName==="INPUT")return;
  if(S&&st&&location.hash.indexOf("#/site/")===0&&st.mode==="cmp"&&st.chg<0&&(e.key==="ArrowUp"||e.key==="ArrowDown")){
    var tg=tagsOf(st.sensor),i=tg.indexOf(st.after)+(e.key==="ArrowUp"?-1:1); if(i>=0&&i<tg.length){st.after=tg[i];drawAll();} e.preventDefault();
  }
});
route();
})();
