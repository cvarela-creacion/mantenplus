/* Optional enquiry flow, prototype message review and accessible component selection. */
(() => {
 const $ = s => document.querySelector(s);
 const dialog = $('#message-dialog');
 window.prepareMessage = text => { $('#message-text').value=text; $('#copy-status').textContent=''; dialog.showModal(); };
 $('#copy-message').addEventListener('click',async()=>{try{await navigator.clipboard.writeText($('#message-text').value);$('#copy-status').textContent='Mensaje copiado.';}catch{$('#message-text').select();$('#copy-status').textContent='Selecciona y copia el texto con el menú de tu dispositivo.';}});
 document.addEventListener('click',e=>{const a=e.target.closest('a');if(!a)return;if(a.href.includes('wa.me/')){e.preventDefault();window.prepareMessage(new URL(a.href).searchParams.get('text')||'Hola MantenPlus, quisiera solicitar una visita.');}if(a.hasAttribute('data-pending-link')){e.preventDefault();window.prepareMessage('Este enlace comercial está pendiente. Puedes preparar una consulta desde el formulario.');}});
 const equipo=$('#request-equipo'),falla=$('#request-falla');
 const issues={};document.querySelectorAll('.service').forEach(card=>{const key=card.querySelector('[data-equipo]').dataset.equipo;issues[key]=[...card.querySelectorAll('.service__tags li')].map(x=>x.textContent);});issues.Secadora=['No seca','No calienta','Hace ruido'];
 const sync=()=>{falla.replaceChildren(...['No estoy seguro',...(issues[equipo.value]||[]),'Otra falla'].map(x=>new Option(x,x)));};
 equipo.addEventListener('change',sync);
 document.querySelectorAll('[data-equipo]').forEach(a=>a.addEventListener('click',()=>{equipo.value=a.dataset.equipo;sync();equipo.focus({preventScroll:true});}));
 $('#request-flow').addEventListener('submit',e=>{e.preventDefault();window.prepareMessage(`Hola MantenPlus, quisiera consultar por una visita.\nEquipo: ${equipo.value||'Por definir'}.\nAvería: ${falla.value}.\nComuna: ${$('#request-comuna').value.trim()||'Por definir'}.`);});
 document.querySelectorAll('[data-dot]').forEach((b,i)=>b.textContent=i+1);
 const explanations=['El cierre debe bloquear la puerta correctamente antes de iniciar el ciclo.','El fuelle sella la unión con la puerta. Revisamos desgaste, residuos y filtraciones.','El tambor aloja la ropa. Su equilibrio ayuda a reducir vibraciones.','La cuba contiene el agua; sus sellos y soportes evitan fugas y movimientos excesivos.','El eje y los rodamientos permiten el giro. Su desgaste puede producir ruido.','El motor controla el giro del tambor. Su diagnóstico incluye conexiones y sensores.','La bomba evacua el agua. El filtro y el impulsor pueden quedar obstruidos.','La placa coordina el funcionamiento y recibe las señales de los sensores.'];
 document.querySelectorAll('[data-part]').forEach((b,i)=>b.addEventListener('click',()=>{document.querySelectorAll('[data-part]').forEach(x=>x.setAttribute('aria-pressed',String(x===b)));document.querySelectorAll('[data-xp-callout]').forEach(x=>x.classList.toggle('is-selected',x.dataset.xpCallout===b.dataset.part));$('#part-detail').textContent=b.querySelector('strong').textContent+': '+explanations[i];}));
})();
