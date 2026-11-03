const $ = id => document.getElementById(id);
let entries = [], current = null, saveTimer = null, tags = [];
const kinds = ["All","To-do","Idea","Memory","Thought","Project","Journal"];
const esc = s => String(s ?? "").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
async function api(url, opts={}) {
  const r = await fetch(url,{headers:{"Content-Type":"application/json"},...opts});
  if(!r.ok) throw new Error((await r.json()).error || "Something went wrong");
  return r.json();
}
function snippet(s){return (s||"").replace(/\s+/g," ").slice(0,105)||"An empty little thought..."}
function niceDate(s){return new Date(s).toLocaleDateString(undefined,{month:"short",day:"numeric"})}
async function loadEntries(){
  const q=$("searchInput").value, kind=document.querySelector(".nav-item.active")?.dataset.kind||"All";
  entries=await api(`/api/entries?q=${encodeURIComponent(q)}&kind=${encodeURIComponent(kind)}`);
  $("allCount").textContent=entries.length;
  $("listCount").textContent=`${entries.length} ${entries.length===1?"note":"notes"}`;
  $("listTitle").textContent=kind==="All"?"Everything":kind+"s";
  renderList();
}
function renderList(){
  $("entryList").innerHTML=entries.map(e=>`<article class="entry-card ${current?.id===e.id?"selected":""}" data-id="${e.id}">
    <h3>${e.is_favorite?"⭐ ":""}${esc(e.title||"Untitled thought")}</h3><p>${esc(snippet(e.body))}</p>
    <div class="entry-meta"><span class="kind-dot">${esc(e.kind)}</span><span>${niceDate(e.updated_at)}</span></div></article>`).join("");
  $("emptyList").style.display=entries.length?"none":"block";
  document.querySelectorAll(".entry-card").forEach(el=>el.onclick=()=>openEntry(el.dataset.id));
}
function clearEditor(){
  current=null;tags=[];$("entryTitle").value="";$("entryBody").value="";$("entryKind").value="Thought";
  $("tagInput").value="";$("tagList").innerHTML="";$("connections").innerHTML="";
  ["connectBtn","favoriteBtn","deleteBtn"].forEach(id=>$(id).disabled=true);
  $("favoriteBtn").textContent="♡ Favorite";$("editorSave").textContent="✦ Ready when you are";
  $("connectionList").innerHTML='<div class="rail-empty">Save a thought, then connect it to another.</div>';
  renderList();
}
async function openEntry(id){
  clearTimeout(saveTimer);
  current=await api(`/api/entries/${id}`);tags=[...current.tags];
  $("entryTitle").value=current.title;$("entryBody").value=current.body;$("entryKind").value=current.kind;
  ["connectBtn","favoriteBtn","deleteBtn"].forEach(id=>$(id).disabled=false);
  $("favoriteBtn").textContent=current.is_favorite?"★ Favorited":"♡ Favorite";
  renderTags();await loadConnections();renderList();
}
function renderTags(){$("tagList").innerHTML=tags.map(t=>`<span class="tag">#${esc(t)}</span>`).join("")}
function scheduleSave(){
  if(!current){saveNewSoon();return}
  $("editorSave").textContent="✦ Saving...";
  clearTimeout(saveTimer);saveTimer=setTimeout(saveCurrent,650);
}
let newDraftTimer=null;
function saveNewSoon(){
  $("editorSave").textContent="✦ Saving your thought...";
  clearTimeout(newDraftTimer);newDraftTimer=setTimeout(async()=>{
    const title=$("entryTitle").value,body=$("entryBody").value;
    if(!title.trim()&&!body.trim()){$("editorSave").textContent="✦ Ready when you are";return}
    const e=await api("/api/entries",{method:"POST",body:JSON.stringify({title,body,kind:$("entryKind").value,tags})});
    current=e;["connectBtn","favoriteBtn","deleteBtn"].forEach(id=>$(id).disabled=false);
    $("editorSave").textContent="✓ Saved on this computer";await loadEntries();renderTags();
  },700);
}
async function saveCurrent(){
  if(!current)return;
  const data={title:$("entryTitle").value,body:$("entryBody").value,kind:$("entryKind").value,tags};
  current=await api(`/api/entries/${current.id}`,{method:"PATCH",body:JSON.stringify(data)});
  $("editorSave").textContent="✓ Saved on this computer";$("saveStatus").textContent="● Saved on this computer";
  await loadEntries();
}
async function loadConnections(){
  if(!current)return;
  const links=await api(`/api/entries/${current.id}/links`);
  $("connectionList").innerHTML=links.length?links.map(e=>`<div class="connection-item" data-id="${e.id}"><strong>${esc(e.title||"Untitled thought")}</strong><small>${esc(e.kind)} · ${niceDate(e.updated_at)}</small></div>`).join(""):'<div class="rail-empty">No connections yet. Connect this thought to another one!</div>';
  document.querySelectorAll(".connection-item").forEach(el=>el.onclick=()=>openEntry(el.dataset.id));
  $("connections").textContent=links.length?`🧵 Connected to ${links.length} ${links.length===1?"thought":"thoughts"}`:"";
}
$("newBtn").onclick=()=>{clearTimeout(saveTimer);clearTimeout(newDraftTimer);clearEditor();$("entryBody").focus()};
$("entryTitle").addEventListener("input",scheduleSave);$("entryBody").addEventListener("input",scheduleSave);$("entryKind").addEventListener("change",scheduleSave);
$("searchInput").addEventListener("input",loadEntries);
document.querySelectorAll(".nav-item").forEach(btn=>btn.onclick=()=>{document.querySelectorAll(".nav-item").forEach(b=>b.classList.remove("active"));btn.classList.add("active");loadEntries()});
$("tagInput").addEventListener("keydown",async e=>{if(e.key==="Enter"){e.preventDefault();const t=e.target.value.trim().replace(/^#/,"");if(t&&!tags.includes(t)){tags.push(t);renderTags();e.target.value="";scheduleSave()}}});
$("favoriteBtn").onclick=async()=>{if(!current)return;current=await api(`/api/entries/${current.id}`,{method:"PATCH",body:JSON.stringify({is_favorite:!current.is_favorite})});$("favoriteBtn").textContent=current.is_favorite?"★ Favorited":"♡ Favorite";loadEntries()};
$("deleteBtn").onclick=async()=>{if(!current||!confirm("Delete this thought?"))return;await api(`/api/entries/${current.id}`,{method:"DELETE"});clearEditor();loadEntries()};
$("connectBtn").onclick=()=>{
 if(!current)return;
 const choices=entries.filter(e=>e.id!==current.id);
 $("modalContent").innerHTML=`<h2>🧵 Connect a thought</h2><p>Find another thought to link to this one. Both notes stay exactly where they are.</p><input id="connectSearch" placeholder="Search your thoughts..."><div id="connectChoices"></div>`;
 const render=()=>{$("connectChoices").innerHTML=choices.filter(e=>(e.title+" "+e.body).toLowerCase().includes($("connectSearch").value.toLowerCase())).map(e=>`<button class="primary connect-choice" data-id="${e.id}" style="display:block;width:100%;margin:6px 0;text-align:left">${esc(e.title||"Untitled thought")} · ${esc(e.kind)}</button>`).join("")||"<p>No matching thoughts yet.</p>";document.querySelectorAll(".connect-choice").forEach(b=>b.onclick=async()=>{await api(`/api/entries/${current.id}/links`,{method:"POST",body:JSON.stringify({target_id:b.dataset.id})});$("modal").classList.add("hidden");loadConnections()})};
 $("connectSearch").oninput=render;render();$("modal").classList.remove("hidden");
};
$("settingsBtn").onclick=()=>{$("modalContent").innerHTML="<h2>⚙️ A little setup</h2><p>Your notes are saved in a local SQLite database on this computer. Google Sheets sync will be added in a later version. For now, nothing leaves your computer.</p><p><strong>Database location:</strong><br>BrainSprinkles/data/brain_sprinkles.db</p>";$("modal").classList.remove("hidden")};
$("modalClose").onclick=()=>$("modal").classList.add("hidden");
$("modal").onclick=e=>{if(e.target===$("modal"))$("modal").classList.add("hidden")};
loadEntries();clearEditor();
