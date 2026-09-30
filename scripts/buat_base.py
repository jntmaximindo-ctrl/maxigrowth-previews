#!/usr/bin/env python3
"""Sekali jalan: ubah contoh baku Atabara (Malaysia) jadi templates/klinik/base.html yang diisi robot.
Setiap penggantian WAJIB cocok tepat n kali (default 1), kalau tidak → gagal (supaya tidak diam-diam rusak)."""
import re, sys, pathlib

src = re.sub(r'data:[^"\')]+', "DATA", pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
out = pathlib.Path(sys.argv[2])
s = src


def R(old, new, n=1, rx=False):
    global s
    c = len(re.findall(old, s, re.S)) if rx else s.count(old)
    if c != n:
        sys.exit(f"GAGAL: {old[:70]!r} ditemukan {c}x, harus {n}x")
    s = re.sub(old, lambda m: new, s, flags=re.S) if rx else s.replace(old, new)


def RX_BLOCK(start, end, new):
    """ganti dari baris yang diawali `start` sampai sebelum baris diawali `end`"""
    global s
    i = s.index("\n" + start) + 1
    j = s.index("\n" + end, i) + 1
    s = s[:i] + new + s[j:]


# ---------- head ----------
R('<title>Atabara Dental Concept</title>', '<title>{{TITLE}}</title>\n<meta name="robots" content="noindex,nofollow">')
R(re.escape('<meta name="description" content="') + r'[^"]*"', '<meta name="description" content="{{DESC}}"', rx=True)

# ---------- preview bar / nav ----------
R('<img src="DATA" alt="Logo Klinik Pergigian Atabara" data-alt="logo_a" width="44" height="44"><div><b>ATABARA</b><small>DENTAL CLINIC</small></div>',
  '<img src="{{LOGO}}" alt="{{NAMA}}" data-alt="logo_a" width="44" height="44"><div><b>{{BRAND1}}</b><small>{{BRAND2}}</small></div>')
R('<button type="button" data-l="ms" aria-pressed="true">BM</button>', '<button type="button" data-l="ms" aria-pressed="true">ID</button>', 2)
R('<div class="links" id="links"><a href="#semak" data-i="n1"></a><a href="#rawatan" data-i="n2"></a><a href="#ansuran" data-i="n3"></a>',
  '<div class="links" id="links"><a href="#semak" data-i="n1"></a><a href="#rawatan" data-i="n2"></a><a href="#{{N3}}" data-i="n3"></a>')
R('<a class="sl" href="#ansuran">', '<a class="sl" href="#{{N3}}">')

# ---------- hero ----------
R('<small>+60 11-6523 6161</small>', '<small>{{TEL_TAMPIL}}</small>')
R('<div class="tlt" aria-hidden="true"><span style="left:0">9</span><span style="left:30.77%">13</span><span style="left:69.23%">18</span><span style="left:100%">22</span></div>',
  '<div class="tlt" id="tlt" aria-hidden="true"></div>')
R('      <img class="badge" src="DATA" alt="">\n', '')
R('<div class="snap" id="snap"><img src="DATA" alt=""><span><i></i>Indera Mahkota 8</span></div>',
  '<div class="snap" id="snap"><span><i></i><em id="snapn">{{SNAP}}</em></span></div>')
# 4 chip bukti → dibuat robot
i = s.index('  <div class="proof rv">'); j = s.index('</div>\n</div></header>', i)
s = s[:i] + '  <div class="proof rv">\n{{PROOF}}\n  ' + s[j:]

# ---------- ansuran & anak ----------
R('<section id="ansuran" style="padding-top:0">', '<section id="ansuran" style="padding-top:0"{{ANS_HIDDEN}}>')
R('<div class="money"><span>RM</span><input id="amt" inputmode="decimal" autocomplete="off" value="5,000"',
  '<div class="money"><span>Rp</span><input id="amt" inputmode="numeric" autocomplete="off" value="{{ANS_MID_T}}"')
R('<input type="range" class="rng" id="rng" min="3000" max="8000" step="100" value="5000"',
  '<input type="range" class="rng" id="rng" min="{{ANS_MIN}}" max="{{ANS_MAX}}" step="{{ANS_STEP}}" value="{{ANS_MID}}"')
R('<div class="rlab"><span>RM3,000</span>', '<div class="rlab"><span>{{ANS_MIN_T}}</span>')
R('<span>RM8,000</span></div>', '<span>{{ANS_MAX_T}}</span></div>')
R('<div class="money"><span>RM</span><input id="dep" inputmode="decimal" autocomplete="off" value="500"',
  '<div class="money"><span>Rp</span><input id="dep" inputmode="numeric" autocomplete="off" value="{{ANS_DEP_T}}"')
R('<div class="kids rv" id="kids">', '<div class="kids rv" id="kids"{{KIDS_HIDDEN}}>')

R('aria-live="polite">RM0</div>', 'aria-live="polite">Rp0</div>')
# ---------- lokasi: foto → peta ----------
R('<h2 data-i="lh"></h2></div><p class="lead" data-i="ll"></p></div>\n  <div class="lg">',
  '<h2 data-i="lh"></h2></div><p class="lead" data-i="ll"></p></div>\n  <div class="cabs" id="cabs" role="group"></div>\n  <div class="lg">')
R('<img src="DATA" alt="Bahagian hadapan Klinik Pergigian Atabara" data-alt="lalt" loading="lazy"><div class="cap" data-i="lcap"></div>',
  '<div class="cap" data-i="lcap"></div>')
R('<div class="vtabs" role="tablist"', '<div class="vtabs" hidden role="tablist"')
R('<button type="button" class="v360" data-v="360">', '<button type="button" class="v360" hidden data-v="360">')
R(r'<p class="adr" id="adr">[^<]*</p>', '<p class="adr" id="adr"></p>', rx=True)
R(r'<a class="btn btn-dark wz" target="_blank" rel="noopener" href="[^"]*">', '<a class="btn btn-dark wz" id="lwz" target="_blank" rel="noopener" href="#">', rx=True)
R(r'<a class="btn btn-ghost" target="_blank" rel="noopener" href="https://www.google.com/maps/search/[^"]*">', '<a class="btn btn-ghost" id="lgm" target="_blank" rel="noopener" href="#">', rx=True)

# ---------- dokter ----------
R('<section class="docs">', '<section class="docs" id="dokter">')
R(r'<a class="glink" target="_blank" rel="noopener" href="https://www.google.com/maps/search/[^"]*">', '<a class="glink" id="glk" target="_blank" rel="noopener" href="#">', rx=True)
old = '<h3>Dr. ____ <span class="chk" data-i="chk"></span></h3>'
if s.count(old) != 3: sys.exit("GAGAL dokter")
for k in (1, 2, 3):
    s = s.replace(old, '<h3>{{DOK%d}}</h3>' % k, 1)
R(r'<ul class="meta">', '<ul class="meta" data-dok>', 3, rx=True)

# ---------- penutup & footer ----------
R('<a class="btn btn-ol" href="tel:+601165236161">', '<a class="btn btn-ol" id="ftel" href="tel:{{TEL_URI}}">')
R('<b>B160 &amp; B162,<br>Taman Mahkota Putra</b>', '<b id="fadr">{{ALAMAT_PENDEK}}</b>')
R('<img src="DATA" alt="" width="52" height="52"><div><b>ATABARA</b><small>DENTAL CLINIC · KUANTAN</small></div></div><p class="ftag">Your Smile Matters</p>',
  '<img src="{{LOGO}}" alt="" width="52" height="52"><div><b>{{BRAND1}}</b><small>{{BRAND2}} · {{KOTA_UP}}</small></div></div><p class="ftag">{{TAGLINE}}</p>')
R('<a class="fa" href="tel:+601165236161"><svg class="i" style="width:16px;height:16px"><use href="#i-phone"/></svg>011-6523 6161</a>',
  '<a class="fa" href="tel:{{TEL_URI}}"><svg class="i" style="width:16px;height:16px"><use href="#i-phone"/></svg>{{TEL_TAMPIL}}</a>')
R('<a class="fa" href="mailto:atabaradentalclinic@gmail.com"><svg class="i" style="width:16px;height:16px"><use href="#i-mail"/></svg>atabaradentalclinic@gmail.com</a>',
  '{{EMAIL_LINK}}')
R(r'<div><h4 data-i="ft_v"></h4><p>[^<]*</p>', '<div><h4 data-i="ft_v"></h4><p id="fadr2">{{ALAMAT}}</p>', rx=True)
R(r'<a class="fa" target="_blank" rel="noopener" href="https://waze.com/ul\?q=[^"]*">Waze</a><a class="fa" target="_blank" rel="noopener" href="https://www.google.com/maps/search/[^"]*">Google Maps</a>',
  '<a class="fa" id="fwz" target="_blank" rel="noopener" href="#">Waze</a><a class="fa" id="fgm" target="_blank" rel="noopener" href="#">Google Maps</a>', rx=True)
i = s.index('<div><h4 data-i="ft_f"></h4>'); j = s.index('\n', i)
s = s[:i] + '{{SOSMED}}' + s[j:]
R('<span>© <span id="yr">2026</span> Klinik Pergigian Atabara</span>', '<span>© <span id="yr">2026</span> {{NAMA}}</span>')

# ---------- JS: data diganti CFG ----------
ico = re.search(r'\nconst ICO=.*\n', s).group(0)
RX_BLOCK('const T={', 'let L="ms";',
         'const CFG=/*@@CFG@@*/null;\n'
         'const T=CFG.T,KEL=CFG.KEL,TR=CFG.TR,FAQ=CFG.FAQ,FIT={ms:TR.map(x=>x.fit.ms),en:TR.map(x=>x.fit.en)};\n'
         'let CI=0,HRS=CFG.CAB[0].HRS,WA=CFG.CAB[0].wa,ADDR=CFG.CAB[0].alamat;\n'
         + ico.strip() + '\n')
R('const WA="601165236161", wa=x=>', 'const wa=x=>')
R(r'\nconst ADDR="[^"]*";', '', rx=True)
R('document.documentElement.lang=L;', 'document.documentElement.lang=L==="ms"?"id":"en";')
R('buildFaq();buildHours();stepper();', 'buildFaq();buildHours();stepper();buildCab();')
R('"atb-lang"', '"mgs-lang"', 2)
# jam lokal klinik (WIB/WITA/WIT)
R('function myt(){const d=new Date(Date.now()+(8*60+', 'function myt(){const d=new Date(Date.now()+(CFG.tz*60+')
R(r'const fmtH=h=>\{.*?\};\n', 'const fmtH=h=>{const hh=Math.floor(h),mm=Math.round((h-hh)*60);if(L==="en"){const ap=hh>=12?"pm":"am";return((hh+11)%12+1)+(mm?":"+String(mm).padStart(2,"0"):"")+ap}return String(hh).padStart(2,"0")+"."+String(mm).padStart(2,"0")};\n'
  'const H0=()=>Math.min(...Object.values(HRS).flat().map(x=>x[0]),24),H1=()=>Math.max(...Object.values(HRS).flat().map(x=>x[1]),0),HS=()=>Math.max(1,H1()-H0()),pc=h=>((h-H0())/HS()*100);\n', rx=True)
R(r'function stInfo\(\)\{.*?\n  return\{c:"st-tutup",tx:t\("closed"\)\}\}',
  'function nextOpen(day){for(let k=1;k<=7;k++){const d=(day+k)%7;if(HRS[d].length)return(k===1?t("tomorrow"):t("days")[d]+" ")+fmtH(HRS[d][0][0])}return""}\n'
  'function stInfo(){const {day,h}=myt(),seg=HRS[day],cur=seg.find(([a,b])=>h>=a&&h<b),next=seg.find(([a])=>a>h);\n'
  '  if(cur)return{c:"st-buka",tx:t("open")+fmtH(cur[1])};\n'
  '  if(next)return{c:"st-rehat",tx:(h<seg[0][0]?t("notyet"):t("rest"))+fmtH(next[0])};\n'
  '  return{c:"st-tutup",tx:t("closed_pre")+nextOpen(day)}}', rx=True)
R('''$("#tls").innerHTML=HRS[day].map(([a,b])=>'<i class="seg" style="left:'+((a-9)/13*100)+'%;width:'+((b-a)/13*100)+'%"></i>').join("");''',
  '''$("#tls").innerHTML=HRS[day].map(([a,b])=>'<i class="seg" style="left:'+pc(a)+'%;width:'+((b-a)/HS()*100)+'%"></i>').join("");
  $("#tlt").innerHTML=[H0(),Math.round((H0()+H1())/2),H1()].map(x=>'<span style="left:'+pc(x)+'%">'+x+'</span>').join("");''')
R('const n=$("#ndl");if(h>=9&&h<=22){n.style.left=((h-9)/13*100)+"%";n.hidden=false}else n.hidden=true}',
  'const n=$("#ndl");if(h>=H0()&&h<=H1()){n.style.left=pc(h)+"%";n.hidden=false}else n.hidden=true}')
# rail dari daftar perawatan
R('const TKI=[0,1,4,5,2,6,7,8,9,3];', 'const TKI=TR.map((x,i)=>i);')
R('const names=t("tk").split(" · ")', 'const names=TR.map(x=>x[L][0].toUpperCase())')
# biaya dalam Rupiah
R('''const fmtFee=p=>'<span class="rm">RM</span>'+''', '''const fmtFee=p=>'<span class="rm">Rp</span>'+''')
R('''const facts=i===5||i===3?['<span>'+t("tf_opg")+'</span>']:i===6?['<span>'+t("tf_inst")+'<span class="chk">'+t("chk")+'</span></span>']:[];''',
  '''const facts=(x.f||[]).map(k=>'<span>'+t(k)+'</span>');''')
R('''(i===6?'<button type="button" class="lnk" data-calc>''', '''(x.calc&&CFG.ans?'<button type="button" class="lnk" data-calc>''')
R('''rm=n=>"RM"+Math.round(n).toLocaleString("en-MY");''', '''rm=n=>"Rp"+Math.round(n).toLocaleString("id-ID");''')
R('''parseFloat(e.value.replace(/[^\\d.]/g,""))''', '''parseFloat(e.value.replace(/\\D/g,""))''')
R('MIN=3000,MAX=8000', 'MIN=CFG.ans?CFG.ans.min:3000000,MAX=CFG.ans?CFG.ans.max:8000000')
R('function goCalc(){amt.value="5,000";setRng(5000);', 'function goCalc(){const m0=CFG.ans?CFG.ans.mid:5000000;amt.value=m0.toLocaleString("id-ID");setRng(m0);')
# FAQ: tanda ✎ per butir
R('([1,3,4,5].includes(i)?', '(FAQ[L][i][2]?')
# jam praktik: ringkasan & strip generik
i = s.index('function buildHours(){'); j = s.index('$("#more").onclick', i)
s = s[:i] + r'''function buildHours(){const {day,h}=myt(),order=[1,2,3,4,5,6,0],fs=d=>HRS[d].length?HRS[d].map(([a,b])=>fmtH(a)+' – '+fmtH(b)).join(", "):t("hol");
  const grp=[];order.forEach(d=>{const v=fs(d),g=grp[grp.length-1];if(g&&g.v===v)g.d.push(d);else grp.push({v,d:[d]})});
  $("#hsum").innerHTML=grp.map(g=>'<tr class="'+(g.d.includes(day)?"today":"")+'"><td>'+t("days")[g.d[0]]+(g.d.length>1?' – '+t("days")[g.d[g.d.length-1]]:'')+'</td><td>'+g.v+'</td></tr>').join("");
  const ax=[H0(),Math.round((H0()+H1())/2),H1()];
  $("#strip").innerHTML='<div class="ax">'+ax.map(x=>'<span style="top:'+pc(x)+'%">'+x+'</span>').join("")+'</div>'+
    order.map(d=>'<div class="dcol'+(d===day?" today":"")+'"><b>'+t("dshort")[d]+'</b><div class="dbar">'+HRS[d].map(([a,b])=>'<i style="top:'+pc(a)+'%;height:'+((b-a)/HS()*100)+'%"></i>').join("")+(d===day&&h>=H0()&&h<=H1()?'<span class="now" style="top:'+pc(h)+'%"></span>':'')+'</div></div>').join("");
  $("#hrs").innerHTML='<caption>'+t("lw")+'</caption>'+order.map(d=>'<tr><th scope="row">'+t("days")[d]+'</th><td>'+(HRS[d].map(([a,b])=>h24(a)+"–"+h24(b)).join(", ")||t("hol"))+'</td></tr>').join("")}
/* ---------- cabang ---------- */
function mapQ(c){return encodeURIComponent(c.q)}
function buildCab(){const c=CFG.CAB[CI],b=$("#cabs");
  $("#adr").textContent=ADDR;$("#fadr2").textContent=ADDR;$("#fadr").textContent=c.pendek;$("#snapn").textContent=c.nama;
  const gm=c.maps||"https://www.google.com/maps/search/?api=1&query="+mapQ(c);
  $("#lgm").href=gm;$("#fgm").href=gm;$("#glk").href=gm;$("#lwz").href=$("#fwz").href="https://waze.com/ul?q="+mapQ(c)+"&navigate=yes";
  if(c.tel){$("#ftel").href="tel:"+c.tel;$$('[data-i="f_call"]').forEach(e=>e.textContent=(L==="ms"?"Telepon ":"Call ")+c.tel_t)}
  if(window.setMap)setMap(c);
  if(CFG.CAB.length<2){b.hidden=true;return}
  b.innerHTML=CFG.CAB.map((x,i)=>'<button type="button" aria-pressed="'+(i===CI)+'" data-c="'+i+'">'+x.nama+'</button>').join("");
  b.querySelectorAll("button").forEach(x=>x.onclick=()=>{CI=+x.dataset.c;const k=CFG.CAB[CI];HRS=k.HRS;WA=k.wa;ADDR=k.alamat;applyLang()})}
''' + s[j:]

R('["top","semak","rawatan","ansuran","lokasi","soalan"]', '["top","semak","rawatan","ansuran","dokter","lokasi","soalan"]')
# ---------- 3D: teks cincin & warna ----------
R('const unit="ATABARA DENTAL CLINIC   ◆   YOUR SMILE MATTERS   ◆   ";', 'const unit=CFG.band+"   ◆   ";')
R("/* ---------- Atabara shield:", "/* ---------- clinic shield:")
# ---------- penampil lokasi → peta ----------
i = s.index('<script>\n(function(){\n  var V=document.getElementById("viewer")'); j = s.index('</script>', i) + len('</script>')
s = s[:i] + '''<script>
(function(){var V=document.getElementById("viewer"),pane=document.getElementById("vpane");if(!V)return;
  window.setMap=function(c){V.classList.add("live");pane.hidden=false;var f=pane.querySelector("iframe");
    if(!f){f=document.createElement("iframe");f.loading="lazy";f.referrerPolicy="no-referrer-when-downgrade";f.title="Peta";pane.appendChild(f)}
    var src="https://maps.google.com/maps?q="+encodeURIComponent(c.q)+"&z=16&output=embed";if(f.src!==src)f.src=src};
  setMap(CFG.CAB[CI]);})();
</script>''' + s[j:]

# CSS tambahan: pemilih cabang & peta
k = s.index('</style>', s.index('DESIGN SYSTEM'))
s = s[:k] + """.cabs{display:flex;flex-wrap:wrap;gap:8px;margin:20px 0 26px;clear:both}.cabs button{padding:10px 16px;border-radius:999px;border:1px solid var(--line2);background:var(--card);font-weight:600;font-size:14px}
.cabs button[aria-pressed="true"]{background:var(--ink);color:#fff;border-color:var(--ink)}
#viewer{min-height:340px;background:var(--gold-l)}#viewer .vpane iframe{width:100%;height:100%;min-height:340px;border:0;display:block}
""" + s[k:]

# sisa jejak Atabara tidak boleh ada
sisa = [m.start() for m in re.finditer(r'(?i)atabara|kuantan|mahkota|6011|601165', s)]
if sisa:
    for p in sisa[:12]:
        print("SISA:", s[max(0, p - 80):p + 60].replace("\n", " "))
    sys.exit(f"GAGAL: {len(sisa)} sisa jejak Atabara")
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(s, encoding="utf-8")
print("OK", len(s), "byte")
