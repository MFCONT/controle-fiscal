/* ── estado global ───────────────────────────────── */
let mesAtual = new Date();
let responsaveis = [];
let charts = {};

/* ── utilidades ──────────────────────────────────── */
const fmt     = d => `${String(d.getMonth()+1).padStart(2,'0')}/${d.getFullYear()}`;
const fmtNome = d => d.toLocaleDateString('pt-BR',{month:'long',year:'numeric'}).replace(/^\w/,c=>c.toUpperCase());
const seg2hm  = s => { s=Math.round(s||0); return `${Math.floor(s/3600)}h${String(Math.floor((s%3600)/60)).padStart(2,'0')}m`; };
const hm2seg  = v => { const [h,m]=(v||'0:0').split(':').map(Number); return (h||0)*3600+(m||0)*60; };

async function api(url, opts={}) {
  const r = await fetch(url, { headers:{'Content-Type':'application/json'}, ...opts });
  if (!r.ok) { const e=await r.json().catch(()=>({erro:'Erro'})); throw new Error(e.erro||r.statusText); }
  return r.json();
}

function toast(msg, tipo='success') {
  const t = document.createElement('div');
  t.className = `alert alert-${tipo} position-fixed bottom-0 end-0 m-3 shadow`;
  t.style.cssText = 'z-index:9999;min-width:220px;font-size:.88rem';
  t.textContent = msg;
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 3000);
}

function classStatus(s) {
  return {Realizada:'st-realizada','Em Andamento':'st-andamento','Não Realizada':'st-nao'}[s]||'st-pendente';
}

function prazoLabel(prazo_dia, status) {
  if (!prazo_dia) return '';
  const m   = mesAtual.getMonth();
  const y   = mesAtual.getFullYear();
  const data = `${String(prazo_dia).padStart(2,'0')}/${String(m+1).padStart(2,'0')}/${y}`;
  if (status === 'Realizada') return `<span class="prazo-ok">${data}</span>`;
  const hoje = new Date(); hoje.setHours(0,0,0,0);
  const venc = new Date(y, m, prazo_dia);
  const diff = Math.ceil((venc-hoje)/(1000*86400));
  if (diff < 0) return `<span class="prazo-late">${data}<br><small>Vencido há ${-diff}d</small></span>`;
  if (diff === 0) return `<span class="prazo-warn">${data}<br><small>Vence hoje</small></span>`;
  if (diff <= 3)  return `<span class="prazo-warn">${data}<br><small>Vence em ${diff}d</small></span>`;
  return `<span class="prazo-ok">${data}</span>`;
}

/* ── navegação de meses ──────────────────────────── */
function atualizarMesLabel() {
  document.getElementById('monthLabel').textContent = fmtNome(mesAtual);
  document.getElementById('relMesAno').value = fmt(mesAtual);
}

document.getElementById('btnAnterior').onclick = () => { mesAtual.setMonth(mesAtual.getMonth()-1); recarregar(); };
document.getElementById('btnProximo').onclick  = () => { mesAtual.setMonth(mesAtual.getMonth()+1); recarregar(); };
document.getElementById('btnPrimeiro').onclick = () => { mesAtual = new Date(mesAtual.getFullYear(),0,1); recarregar(); };
document.getElementById('btnHoje').onclick     = () => { mesAtual = new Date(); recarregar(); };

/* ── sidebar toggle ──────────────────────────────── */
document.getElementById('btnMenu').onclick = () => {
  document.getElementById('sidebar').classList.toggle('collapsed');
};

/* ── tabs ────────────────────────────────────────── */
document.querySelectorAll('.nav-item[data-tab]').forEach(a => {
  a.addEventListener('click', e => {
    e.preventDefault();
    document.querySelectorAll('.nav-item').forEach(x=>x.classList.remove('active'));
    a.classList.add('active');
    const id = a.dataset.tab;
    document.querySelectorAll('.tab-pane').forEach(p=>p.classList.remove('active'));
    document.getElementById('tab-'+id).classList.add('active');
    if (id==='dashboard') carregarDashboard();
    if (id==='calendario') carregarCalendario();
    if (id==='descricoes') carregarDescricoes();
    if (id==='gerenciar') carregarGerenciar();
  });
});

/* ── gerenciar sub-tabs ──────────────────────────── */
document.querySelectorAll('[data-ger]').forEach(a => {
  a.addEventListener('click', e => {
    e.preventDefault();
    document.querySelectorAll('[data-ger]').forEach(x=>x.classList.remove('active'));
    a.classList.add('active');
    document.querySelectorAll('.ger-pane').forEach(p=>p.classList.remove('active'));
    document.getElementById('ger-'+a.dataset.ger).classList.add('active');
    if (a.dataset.ger==='ocultas') carregarOcultas();
    if (a.dataset.ger==='usuarios' && IS_ADMIN) carregarUsuarios();
  });
});

/* ── carregamento principal ──────────────────────── */
async function carregarAtividades() {
  const resp = document.getElementById('filtroResp').value;
  const st   = document.getElementById('filtroStatus').value;
  const data = await api(`/api/atividades?mes_ano=${fmt(mesAtual)}&responsavel=${encodeURIComponent(resp)}&status=${encodeURIComponent(st)}`);
  renderTabela(data);
  renderCards(data);
  verificarVencimentos(data);
}

function renderCards(ativs) {
  const cnt = {Realizada:0,Pendente:0,'Em Andamento':0,'Não Realizada':0};
  ativs.forEach(a => cnt[a.status] = (cnt[a.status]||0)+1);
  const total = ativs.length;
  const pct   = total ? Math.round(cnt.Realizada/total*100) : 0;
  document.getElementById('summaryCards').innerHTML = `
    <div class="sum-card azul"><div class="sc-label">Total</div><div class="sc-value">${total}</div></div>
    <div class="sum-card verde"><div class="sc-label">Realizadas</div><div class="sc-value">${cnt.Realizada}</div></div>
    <div class="sum-card amarelo"><div class="sc-label">Em Andamento</div><div class="sc-value">${cnt['Em Andamento']}</div></div>
    <div class="sum-card cinza"><div class="sc-label">Pendentes</div><div class="sc-value">${cnt.Pendente}</div></div>
    <div class="sum-card vermelho"><div class="sc-label">Não Realizadas</div><div class="sc-value">${cnt['Não Realizada']}</div></div>
    <div class="sum-card ${pct>=80?'verde':pct>=50?'amarelo':'vermelho'}"><div class="sc-label">Conclusão</div><div class="sc-value">${pct}%</div></div>
  `;
}

function podeEditar(atividade) {
  if (IS_ADMIN) return true;
  return USER_RESP && atividade.responsavel === USER_RESP;
}

function renderTabela(ativs) {
  const tbody = document.getElementById('tbodyAtiv');
  if (!ativs.length) {
    tbody.innerHTML = '<tr><td colspan="9" class="text-center text-muted py-4">Nenhuma atividade encontrada.</td></tr>';
    return;
  }
  tbody.innerHTML = ativs.map(a => {
    const tempo = a.tempo_seg ? seg2hm(a.tempo_seg) : '—';
    const prazo = prazoLabel(a.prazo_dia, a.status);
    const conc  = a.data_conclusao ? `<br><small class="text-muted">${a.data_conclusao.replace('T',' ')}</small>` : '';
    const botoes = podeEditar(a)
      ? `<button class="btn-tbl" title="Editar registro" onclick="abrirEditar(${a.id})"><i class="bi bi-pencil"></i></button>
         ${a.tipo==='Diária' ? `<button class="btn-tbl" title="Marcar dias realizados" onclick="abrirDiasAtiv(${a.id},'${a.nome.replace(/'/g,"\\'")}')"><i class="bi bi-calendar-check"></i></button>` : ''}
         <button class="btn-tbl danger" title="Ocultar" onclick="ocultarAtividade(${a.id},'${a.nome.replace(/'/g,"\\'")}')"><i class="bi bi-eye-slash"></i></button>
         ${IS_ADMIN ? `<button class="btn-tbl danger" title="Excluir permanente" onclick="excluirPermanente(${a.id},'${a.nome.replace(/'/g,"\\'")}')"><i class="bi bi-trash"></i></button>` : ''}`
      : '<span class="text-muted small">—</span>';
    return `<tr>
      <td><span class="fw-semibold">${a.responsavel}</span></td>
      <td>${a.nome}</td>
      <td><span class="badge bg-secondary bg-opacity-10 text-secondary">${a.tipo}</span></td>
      <td>${prazo||'—'}</td>
      <td><span class="badge-status ${classStatus(a.status)}">${a.status}</span>${conc}</td>
      <td>${tempo}</td>
      <td class="text-muted" style="max-width:120px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${a.obs||'—'}</td>
      <td style="white-space:nowrap">${botoes}</td>
    </tr>`;
  }).join('');
}

function verificarVencimentos(ativs) {
  const hoje = new Date();
  const venc = ativs.filter(a => {
    if (!a.prazo_dia || a.status==='Realizada') return false;
    const d = new Date(hoje.getFullYear(), hoje.getMonth(), a.prazo_dia);
    return (d-hoje)/(1000*86400) <= 3;
  });
  const el = document.getElementById('alertaVencimento');
  if (venc.length) {
    el.textContent = `${venc.length} prazo(s) urgente(s)`;
    el.style.display = '';
  } else el.style.display = 'none';
}

/* ── modal editar/criar ──────────────────────────── */
let modalAtivBS;
document.addEventListener('DOMContentLoaded', () => {
  modalAtivBS = new bootstrap.Modal(document.getElementById('modalAtiv'));
});

function abrirEditar(id) {
  api(`/api/atividades?mes_ano=${fmt(mesAtual)}`).then(ativs => {
    const a = ativs.find(x=>x.id===id);
    if (!a) return;
    document.getElementById('modalAtivTitulo').textContent = 'Editar Atividade';
    document.getElementById('editId').value = id;
    document.getElementById('editStatus').value = a.status;
    const t = Math.round(a.tempo_seg||0);
    document.getElementById('editTempo').value = t ? `${Math.floor(t/3600)}:${String(Math.floor((t%3600)/60)).padStart(2,'0')}` : '';
    document.getElementById('editObs').value = a.obs||'';
    document.getElementById('editConclusao').value = a.data_conclusao||'';

    if (IS_ADMIN) {
      document.getElementById('secaoAtividade').style.display = '';
      document.getElementById('nomeAtivReadonly').style.display = 'none';
      document.getElementById('editNome').value = a.nome;
      document.getElementById('editTipo').value = a.tipo;
      document.getElementById('editPrazo').value = a.prazo_dia||'';
      preencherSelectResp('editResp', a.responsavel);
    } else {
      document.getElementById('secaoAtividade').style.display = 'none';
      document.getElementById('nomeAtivReadonly').style.display = '';
      document.getElementById('editNomeLbl').textContent = `${a.responsavel} — ${a.nome}`;
    }

    // seção replicar (só para atividades existentes)
    document.getElementById('secaoReplicar').style.display = '';
    document.getElementById('chkReplicar').checked = false;
    document.getElementById('replicarOpcoes').style.display = 'none';
    construirMesesReplicar();

    modalAtivBS.show();
  });
}

function construirMesesReplicar() {
  const lista = document.getElementById('replicarMesesLista');
  lista.innerHTML = '';
  const hoje = mesAtual;
  for (let i = 1; i <= 6; i++) {
    const d = new Date(hoje.getFullYear(), hoje.getMonth() + i, 1);
    const ma = fmt(d);
    const nome = d.toLocaleDateString('pt-BR',{month:'short',year:'numeric'});
    const cb = document.createElement('div');
    cb.className = 'form-check form-check-inline';
    cb.innerHTML = `<input class="form-check-input replicar-mes" type="checkbox" value="${ma}" id="rm_${ma}">
                    <label class="form-check-label" for="rm_${ma}">${nome}</label>`;
    lista.appendChild(cb);
  }
}

document.getElementById('chkReplicar').addEventListener('change', function() {
  document.getElementById('replicarOpcoes').style.display = this.checked ? '' : 'none';
});

function preencherSelectResp(id, selecionado) {
  const sel = document.getElementById(id);
  sel.innerHTML = responsaveis.map(r =>
    `<option value="${r.nome}" ${r.nome===selecionado?'selected':''}>${r.nome}</option>`
  ).join('');
}

document.getElementById('btnNovaAtividade').onclick = () => {
  if (!IS_ADMIN) { toast('Apenas o administrador pode criar novas atividades.','warning'); return; }
  document.getElementById('modalAtivTitulo').textContent = 'Nova Atividade';
  document.getElementById('editId').value = '';
  document.getElementById('secaoAtividade').style.display = '';
  document.getElementById('nomeAtivReadonly').style.display = 'none';
  document.getElementById('secaoReplicar').style.display = 'none';
  ['editNome','editTempo','editObs','editPrazo','editConclusao'].forEach(id => document.getElementById(id).value='');
  document.getElementById('editStatus').value = 'Pendente';
  preencherSelectResp('editResp', responsaveis[0]?.nome||'');
  modalAtivBS.show();
};

document.getElementById('btnSalvarAtiv').onclick = async () => {
  const id      = document.getElementById('editId').value;
  const status  = document.getElementById('editStatus').value;
  const tempo   = hm2seg(document.getElementById('editTempo').value);
  const obs     = document.getElementById('editObs').value.trim();
  const concl   = document.getElementById('editConclusao').value;

  if (!id) {
    // Nova atividade (só admin)
    const nome  = document.getElementById('editNome').value.trim();
    const resp  = document.getElementById('editResp').value;
    const tipo  = document.getElementById('editTipo').value;
    const prazo = document.getElementById('editPrazo').value||null;
    if (!nome || !resp) { toast('Preencha nome e responsável.','warning'); return; }
    try {
      const res = await api('/api/atividades', {method:'POST',
        body: JSON.stringify({responsavel:resp,nome,tipo,prazo_dia:prazo?+prazo:null})});
      await api('/api/registros', {method:'POST',
        body: JSON.stringify({atividade_id:res.id,mes_ano:fmt(mesAtual),status,tempo_seg:tempo,obs,data_conclusao:concl})});
      modalAtivBS.hide();
      toast('Atividade criada.');
      carregarAtividades();
    } catch(e) { toast(e.message,'danger'); }
    return;
  }

  // Edição de atividade existente
  try {
    if (IS_ADMIN) {
      const nome  = document.getElementById('editNome').value.trim();
      const resp  = document.getElementById('editResp').value;
      const tipo  = document.getElementById('editTipo').value;
      const prazo = document.getElementById('editPrazo').value||null;
      await api(`/api/atividades/${id}`, {method:'PUT',
        body: JSON.stringify({responsavel:resp,nome,tipo,prazo_dia:prazo?+prazo:null})});
    }
    await api('/api/registros', {method:'POST',
      body: JSON.stringify({atividade_id:+id,mes_ano:fmt(mesAtual),status,tempo_seg:tempo,obs,data_conclusao:concl})});

    // replicar para outros meses?
    if (document.getElementById('chkReplicar').checked) {
      const meses = [...document.querySelectorAll('.replicar-mes:checked')].map(c=>c.value);
      if (meses.length) {
        await api('/api/registros/replicar', {method:'POST',
          body: JSON.stringify({atividade_id:+id, mes_ano_origem:fmt(mesAtual), meses_destino:meses})});
        toast(`Replicado para ${meses.length} mês(es).`);
      }
    }

    modalAtivBS.hide();
    toast('Salvo com sucesso.');
    carregarAtividades();
  } catch(e) { toast(e.message,'danger'); }
};

async function ocultarAtividade(id, nome) {
  if (!confirm(`Ocultar "${nome}" deste mês em diante?`)) return;
  await api(`/api/atividades/${id}`, {method:'DELETE'});
  toast('Atividade ocultada.');
  carregarAtividades();
}

async function excluirPermanente(id, nome) {
  if (!IS_ADMIN) return;
  if (!confirm(`EXCLUIR PERMANENTEMENTE "${nome}"?\n\nEsta ação não pode ser desfeita e removerá todos os registros históricos.`)) return;
  await api(`/api/atividades/${id}?permanente=1`, {method:'DELETE'});
  toast('Atividade excluída permanentemente.');
  carregarAtividades();
}

/* ── filtros ─────────────────────────────────────── */
document.getElementById('filtroResp').onchange   = carregarAtividades;
document.getElementById('filtroStatus').onchange = carregarAtividades;

/* ── dashboard ───────────────────────────────────── */
async function carregarDashboard() {
  const [stats, tend] = await Promise.all([
    api(`/api/stats?mes_ano=${fmt(mesAtual)}`),
    api('/api/tendencia')
  ]);

  const cnt = stats.contagem;
  const cores = ['#28a745','#6c757d','#ffc107','#dc3545'];

  destroyChart('chartStatus');
  charts.chartStatus = new Chart(document.getElementById('chartStatus'), {
    type:'doughnut',
    data:{ labels:['Realizada','Pendente','Em Andamento','Não Realizada'],
           datasets:[{data:[cnt.Realizada||0,cnt.Pendente||0,cnt['Em Andamento']||0,cnt['Não Realizada']||0],
                      backgroundColor:cores,borderWidth:2}]},
    options:{plugins:{legend:{position:'bottom'}},cutout:'60%'}
  });

  const nomes = Object.keys(stats.tempo_por_responsavel);
  const tempos = nomes.map(n => Math.round((stats.tempo_por_responsavel[n]||0)/60));
  destroyChart('chartHoras');
  charts.chartHoras = new Chart(document.getElementById('chartHoras'), {
    type:'bar',
    data:{ labels:nomes, datasets:[{label:'Minutos',data:tempos,
           backgroundColor:'#2e75b6',borderRadius:6}]},
    options:{plugins:{legend:{display:false}},scales:{y:{beginAtZero:true}}}
  });

  destroyChart('chartResp');
  const atMes = await api(`/api/atividades?mes_ano=${fmt(mesAtual)}`);
  const byResp = {};
  atMes.forEach(a=>{ byResp[a.responsavel]=(byResp[a.responsavel]||{tot:0,real:0}); byResp[a.responsavel].tot++; if(a.status==='Realizada') byResp[a.responsavel].real++; });
  const rn = Object.keys(byResp);
  charts.chartResp = new Chart(document.getElementById('chartResp'), {
    type:'bar',
    data:{ labels:rn, datasets:[
      {label:'Total',data:rn.map(r=>byResp[r].tot),backgroundColor:'#6c757d55',borderRadius:4},
      {label:'Realizadas',data:rn.map(r=>byResp[r].real),backgroundColor:'#28a745',borderRadius:4}
    ]},
    options:{plugins:{legend:{position:'bottom'}},scales:{y:{beginAtZero:true}}}
  });

  destroyChart('chartTend');
  charts.chartTend = new Chart(document.getElementById('chartTend'), {
    type:'line',
    data:{ labels:tend.map(t=>t.mes_ano), datasets:[
      {label:'Realizadas',data:tend.map(t=>t.realizadas),borderColor:'#28a745',backgroundColor:'#28a74522',fill:true,tension:.3,pointRadius:4},
      {label:'Total',data:tend.map(t=>t.total),borderColor:'#2e75b6',backgroundColor:'#2e75b622',fill:false,tension:.3,borderDash:[5,3],pointRadius:4}
    ]},
    options:{plugins:{legend:{position:'bottom'}},scales:{y:{beginAtZero:true}}}
  });
}

function destroyChart(id) {
  if (charts[id]) { charts[id].destroy(); delete charts[id]; }
}

/* ── relatório PDF ───────────────────────────────── */
document.getElementById('btnGerarPdf').onclick = () => {
  const resp = encodeURIComponent(document.getElementById('relResp').value);
  window.open(`/api/relatorio/pdf?mes_ano=${fmt(mesAtual)}&responsavel=${resp}`, '_blank');
};

/* ── gerenciar ───────────────────────────────────── */
async function carregarGerenciar() {
  await carregarResponsaveis();
}

async function carregarResponsaveis() {
  const data = await api('/api/responsaveis');
  responsaveis = data;
  ['filtroResp','relResp','calFiltroResp','descFiltroResp'].forEach(id => {
    const sel = document.getElementById(id);
    const val = sel.value;
    if (['filtroResp','calFiltroResp','descFiltroResp'].includes(id)) sel.innerHTML = '<option value="Todos">Todos os responsáveis</option>';
    else sel.innerHTML = '<option value="Todos">Todos</option>';
    data.forEach(r => sel.innerHTML += `<option value="${r.nome}" ${r.nome===val?'selected':''}>${r.nome}</option>`);
  });

  // popula select de responsável no modal de usuário
  const selUserResp = document.getElementById('novoUserResp');
  if (selUserResp) {
    selUserResp.innerHTML = '<option value="">— nenhum (admin) —</option>';
    data.forEach(r => selUserResp.innerHTML += `<option value="${r.nome}">${r.nome}</option>`);
  }

  document.getElementById('listaResps').innerHTML = data.map(r => `
    <div class="ger-item">
      <div class="color-dot" style="background:${r.cor}"></div>
      <span class="ger-nome">${r.nome}</span>
      <button class="btn btn-sm btn-outline-danger" onclick="excluirResp(${r.id},'${r.nome.replace(/'/g,"\\'")}')">
        <i class="bi bi-trash"></i>
      </button>
    </div>`).join('');
}

async function excluirResp(id, nome) {
  if (!confirm(`Excluir responsável "${nome}"? Suas atividades personalizadas serão ocultadas.`)) return;
  const r = await api(`/api/responsaveis/${id}`, {method:'DELETE'});
  if (!r.ok) { toast('Não é possível excluir responsáveis padrão.','warning'); return; }
  toast('Responsável excluído.');
  carregarResponsaveis();
}

let modalRespBS;
document.addEventListener('DOMContentLoaded', () => {
  modalRespBS = new bootstrap.Modal(document.getElementById('modalResp'));
});
document.getElementById('btnNovoResp').onclick = () => modalRespBS.show();
document.getElementById('btnSalvarResp').onclick = async () => {
  const nome = document.getElementById('novoRespNome').value.trim();
  const cor  = document.getElementById('novoRespCor').value;
  if (!nome) { toast('Digite o nome.','warning'); return; }
  try {
    await api('/api/responsaveis', {method:'POST', body:JSON.stringify({nome,cor})});
    modalRespBS.hide();
    document.getElementById('novoRespNome').value='';
    toast('Responsável criado.');
    carregarResponsaveis();
  } catch(e) { toast(e.message,'danger'); }
};

async function carregarOcultas() {
  const data = await api('/api/atividades/ocultas');
  document.getElementById('listaOcultas').innerHTML = data.length
    ? data.map(a => `
        <div class="ger-item">
          <span class="ger-nome">${a.responsavel} — ${a.nome}</span>
          <button class="btn btn-sm btn-outline-success" onclick="restaurarAtiv(${a.id})">
            <i class="bi bi-arrow-counterclockwise"></i> Restaurar
          </button>
        </div>`).join('')
    : '<p class="text-muted">Nenhuma atividade oculta.</p>';
}

async function restaurarAtiv(id) {
  await api(`/api/atividades/${id}/restaurar`, {method:'POST'});
  toast('Atividade restaurada.');
  carregarOcultas();
  carregarAtividades();
}

/* ── usuários ────────────────────────────────────── */
async function carregarUsuarios() {
  if (!IS_ADMIN) return;
  const data = await api('/api/usuarios');
  document.getElementById('listaUsuarios').innerHTML = data.map(u => `
    <div class="ger-item">
      <span class="fw-semibold ger-nome">${u.nome}</span>
      ${u.admin ? '<span class="badge bg-primary">Admin</span>' : ''}
      ${u.responsavel_nome ? `<span class="badge bg-secondary">${u.responsavel_nome}</span>` : ''}
      <button class="btn btn-sm btn-outline-danger" onclick="excluirUsuario(${u.id},'${u.nome.replace(/'/g,"\\'")}')">
        <i class="bi bi-trash"></i>
      </button>
    </div>`).join('');
}

async function excluirUsuario(id, nome) {
  if (!confirm(`Excluir usuário "${nome}"?`)) return;
  await api(`/api/usuarios/${id}`, {method:'DELETE'});
  toast('Usuário excluído.');
  carregarUsuarios();
}

let modalUserBS;
document.addEventListener('DOMContentLoaded', () => {
  if (IS_ADMIN) modalUserBS = new bootstrap.Modal(document.getElementById('modalUsuario'));
});
document.getElementById('btnNovoUsuario')?.addEventListener('click', () => modalUserBS.show());
document.getElementById('btnSalvarUsuario')?.addEventListener('click', async () => {
  const nome      = document.getElementById('novoUserNome').value.trim();
  const senha     = document.getElementById('novoUserSenha').value;
  const adm       = document.getElementById('novoUserAdmin').checked ? 1 : 0;
  const respNome  = document.getElementById('novoUserResp').value;
  if (!nome||!senha) { toast('Preencha nome e senha.','warning'); return; }
  try {
    await api('/api/usuarios', {method:'POST', body:JSON.stringify({nome,senha,admin:adm,responsavel_nome:respNome})});
    modalUserBS.hide();
    document.getElementById('novoUserNome').value='';
    document.getElementById('novoUserSenha').value='';
    toast('Usuário criado.');
    carregarUsuarios();
  } catch(e) { toast(e.message,'danger'); }
});

/* ── alterar senha ───────────────────────────────── */
document.getElementById('btnSalvarSenha').onclick = async () => {
  const nova  = document.getElementById('novaSenha').value;
  const conf  = document.getElementById('confirmarSenha').value;
  if (!nova) { toast('Digite a nova senha.','warning'); return; }
  if (nova !== conf) { toast('Senhas não conferem.','danger'); return; }
  await api('/api/senha', {method:'POST', body:JSON.stringify({nova_senha:nova})});
  document.getElementById('novaSenha').value='';
  document.getElementById('confirmarSenha').value='';
  toast('Senha alterada com sucesso.');
};

/* ── calendário ──────────────────────────────────── */
let modalDiaBS;
document.addEventListener('DOMContentLoaded', () => {
  modalDiaBS = new bootstrap.Modal(document.getElementById('modalDia'));
});

async function carregarCalendario() {
  const respFiltro = document.getElementById('calFiltroResp').value;
  const atividades = await api(`/api/atividades?mes_ano=${fmt(mesAtual)}&responsavel=${encodeURIComponent(respFiltro)}`);

  const porDia = {};
  atividades.forEach(a => {
    if (!a.prazo_dia) return;
    if (!porDia[a.prazo_dia]) porDia[a.prazo_dia] = [];
    porDia[a.prazo_dia].push(a);
  });

  const ano = mesAtual.getFullYear();
  const mes = mesAtual.getMonth();
  const hoje = new Date();

  const primeiroDia  = new Date(ano, mes, 1);
  const ultimoDia    = new Date(ano, mes + 1, 0);
  const diasNoMes    = ultimoDia.getDate();
  // calendário segunda-feira primeiro: dom(0)→6, seg(1)→0, ..., sab(6)→5
  const inicioSemana = (primeiroDia.getDay() + 6) % 7;

  const grid = document.getElementById('calGrid');
  grid.innerHTML = '';

  const totalCelulas = Math.ceil((inicioSemana + diasNoMes) / 7) * 7;

  for (let i = 0; i < totalCelulas; i++) {
    const diaDiff   = i - inicioSemana;
    const data      = new Date(ano, mes, 1 + diaDiff);
    const diaNum    = data.getDate();
    const ehMesAtual = data.getMonth() === mes;
    const ehHoje    = data.toDateString() === hoje.toDateString();

    const cell = document.createElement('div');
    cell.className = 'cal-cell' +
      (!ehMesAtual ? ' outro-mes' : '') +
      (ehHoje      ? ' hoje'      : '');

    const numEl = document.createElement('div');
    numEl.className = 'cal-dia-num';
    numEl.textContent = diaNum;
    cell.appendChild(numEl);

    const eventosEl = document.createElement('div');
    eventosEl.className = 'cal-eventos';

    if (ehMesAtual && porDia[diaNum]) {
      const lista = porDia[diaNum];
      const MAX_VIS = 3;
      lista.slice(0, MAX_VIS).forEach(a => {
        const ev = document.createElement('div');
        const cls = {'Realizada':'ev-realizada','Em Andamento':'ev-andamento','Não Realizada':'ev-nao','Pendente':'ev-pendente'}[a.status]||'ev-pendente';
        ev.className = `cal-evento ${cls}`;
        ev.textContent = `${a.responsavel.split(' ')[0]}: ${a.nome}`;
        ev.title = `${a.responsavel} — ${a.nome} (${a.status})`;
        ev.onclick = (e) => { e.stopPropagation(); abrirModalDia(diaNum, lista); };
        eventosEl.appendChild(ev);
      });
      if (lista.length > MAX_VIS) {
        const mais = document.createElement('div');
        mais.className = 'cal-mais';
        mais.textContent = `+${lista.length - MAX_VIS} mais`;
        mais.onclick = (e) => { e.stopPropagation(); abrirModalDia(diaNum, lista); };
        eventosEl.appendChild(mais);
      }
    }

    cell.appendChild(eventosEl);

    if (ehMesAtual && porDia[diaNum]) {
      cell.style.cursor = 'pointer';
      cell.onclick = () => abrirModalDia(diaNum, porDia[diaNum]);
    }

    grid.appendChild(cell);
  }
}

function abrirModalDia(dia, atividades) {
  const mes  = mesAtual.toLocaleDateString('pt-BR', {month:'long', year:'numeric'});
  const data = `${String(dia).padStart(2,'0')} de ${mes}`;
  document.getElementById('modalDiaTitulo').textContent = data;
  document.getElementById('modalDiaHeader').style.background = 'var(--primary)';
  document.getElementById('modalDiaHeader').style.color = '#fff';

  document.getElementById('modalDiaBody').innerHTML = atividades.map(a => {
    const cls   = classStatus(a.status);
    const tempo = a.tempo_seg ? seg2hm(a.tempo_seg) : '—';
    const editBtn = podeEditar(a)
      ? `<button class="btn-tbl" onclick="abrirEditar(${a.id});bootstrap.Modal.getInstance(document.getElementById('modalDia')).hide()"><i class="bi bi-pencil"></i></button>`
      : '';
    return `<tr>
      <td class="fw-semibold">${a.responsavel}</td>
      <td>${a.nome}</td>
      <td><span class="badge bg-secondary bg-opacity-10 text-secondary">${a.tipo}</span></td>
      <td><span class="badge-status ${cls}">${a.status}</span></td>
      <td>${tempo}</td>
      <td>${editBtn}</td>
    </tr>`;
  }).join('');

  modalDiaBS.show();
}

document.getElementById('calFiltroResp').onchange = () => {
  if (document.getElementById('tab-calendario').classList.contains('active')) {
    carregarCalendario();
  }
};

/* ── modal de dias (atividades diárias) ──────────── */
let modalDiasAtivBS, diasSelecionados = new Set(), diasComRegistro = new Set();

document.addEventListener('DOMContentLoaded', () => {
  modalDiasAtivBS = new bootstrap.Modal(document.getElementById('modalDiasAtiv'));
});

async function abrirDiasAtiv(aid, nome) {
  document.getElementById('diasAtivId').value = aid;
  document.getElementById('modalDiasAtivTitulo').textContent = `Dias realizados — ${nome}`;
  document.getElementById('diasAtivObs').value = '';
  document.getElementById('diasAtivStatus').value = 'Realizada';

  const registros = await api(`/api/registros/dia?atividade_id=${aid}&mes_ano=${fmt(mesAtual)}`);
  diasSelecionados = new Set(registros.map(r => r.data));
  diasComRegistro  = new Set(registros.map(r => r.data));

  renderDiasGrid();
  modalDiasAtivBS.show();
}

function renderDiasGrid() {
  const ano = mesAtual.getFullYear();
  const mes = mesAtual.getMonth();
  const primeiroDia = new Date(ano, mes, 1);
  const diasNoMes   = new Date(ano, mes + 1, 0).getDate();
  const inicioSemana = (primeiroDia.getDay() + 6) % 7;

  const container = document.getElementById('diasAtivGrid');
  container.innerHTML = '';

  // cabeçalho
  const hdr = document.createElement('div');
  hdr.className = 'dias-grid-header';
  ['Seg','Ter','Qua','Qui','Sex','Sáb','Dom'].forEach(d => {
    const el = document.createElement('div');
    el.textContent = d;
    hdr.appendChild(el);
  });
  container.appendChild(hdr);

  const grid = document.createElement('div');
  grid.className = 'dias-grid';
  const total = Math.ceil((inicioSemana + diasNoMes) / 7) * 7;

  for (let i = 0; i < total; i++) {
    const btn = document.createElement('button');
    const diaN = i - inicioSemana + 1;
    const ehMes = diaN >= 1 && diaN <= diasNoMes;
    btn.className = 'dia-btn' + (!ehMes ? ' outro-mes-dia' : '');
    btn.textContent = ehMes ? diaN : '';

    if (ehMes) {
      const dataFmt = `${String(diaN).padStart(2,'0')}/${String(mes+1).padStart(2,'0')}/${ano}`;
      if (diasComRegistro.has(dataFmt)) {
        btn.classList.add('tem-registro');
        const dot = document.createElement('div');
        dot.className = 'dia-dot';
        btn.appendChild(dot);
      }
      if (diasSelecionados.has(dataFmt)) btn.classList.add('selecionado');
      btn.onclick = () => {
        if (diasSelecionados.has(dataFmt)) {
          diasSelecionados.delete(dataFmt);
          btn.classList.remove('selecionado');
        } else {
          diasSelecionados.add(dataFmt);
          btn.classList.add('selecionado');
        }
        document.getElementById('diasAtivContador').textContent =
          `${diasSelecionados.size} dia(s) selecionado(s)`;
      };
    }
    grid.appendChild(btn);
  }
  container.appendChild(grid);
  document.getElementById('diasAtivContador').textContent =
    `${diasSelecionados.size} dia(s) selecionado(s)`;
}

document.getElementById('btnSalvarDias').onclick = async () => {
  const aid    = +document.getElementById('diasAtivId').value;
  const status = document.getElementById('diasAtivStatus').value;
  const obs    = document.getElementById('diasAtivObs').value.trim();

  const add = [...diasSelecionados].filter(d => !diasComRegistro.has(d));
  const rem = [...diasComRegistro].filter(d => !diasSelecionados.has(d));

  try {
    await api('/api/registros/dia', {method:'POST',
      body: JSON.stringify({atividade_id:aid, mes_ano:fmt(mesAtual),
                            datas_add:add, datas_rem:rem, status, obs})});
    modalDiasAtivBS.hide();
    toast(`${diasSelecionados.size} dia(s) salvos.`);
    carregarAtividades();
    if (document.getElementById('tab-calendario').classList.contains('active'))
      carregarCalendario();
  } catch(e) { toast(e.message,'danger'); }
};

/* ── aba descrições ──────────────────────────────── */
let modalDescricaoBS;
document.addEventListener('DOMContentLoaded', () => {
  modalDescricaoBS = new bootstrap.Modal(document.getElementById('modalDescricao'));
});

async function carregarDescricoes() {
  const resp = document.getElementById('descFiltroResp').value;
  const data = await api(`/api/descricoes?responsavel=${encodeURIComponent(resp)}`);

  // agrupa por responsável
  const grupos = {};
  data.forEach(a => {
    if (!grupos[a.responsavel]) grupos[a.responsavel] = [];
    grupos[a.responsavel].push(a);
  });

  const container = document.getElementById('descricoesList');
  container.innerHTML = Object.entries(grupos).map(([resp, ativs]) => `
    <div class="desc-grupo">
      <div class="desc-grupo-titulo"><i class="bi bi-person-fill"></i> ${resp}</div>
      ${ativs.map(a => {
        const podeEdit = IS_ADMIN || USER_RESP === a.responsavel;
        const texto = a.descricao || '';
        return `<div class="desc-item">
          <div>
            <div class="desc-item-nome">${a.nome}</div>
            <div class="desc-item-tipo">${a.tipo}</div>
          </div>
          <div class="desc-item-texto ${texto ? '' : 'vazio'}">${texto || 'Sem descrição cadastrada.'}</div>
          ${podeEdit ? `<button class="btn btn-sm btn-outline-primary btn-desc-edit"
            onclick="abrirDescricao(${a.id},'${a.nome.replace(/'/g,"\\'")}','${(a.descricao||'').replace(/'/g,"\\'").replace(/\n/g,'\\n')}')">
            <i class="bi bi-pencil"></i></button>` : ''}
        </div>`;
      }).join('')}
    </div>`).join('');
}

function abrirDescricao(aid, nome, textoAtual) {
  document.getElementById('descricaoAid').value = aid;
  document.getElementById('modalDescricaoTitulo').textContent = nome;
  document.getElementById('descricaoTexto').value = textoAtual.replace(/\\n/g, '\n');
  modalDescricaoBS.show();
}

document.getElementById('btnSalvarDescricao').onclick = async () => {
  const aid  = +document.getElementById('descricaoAid').value;
  const desc = document.getElementById('descricaoTexto').value.trim();
  try {
    await api(`/api/atividades/${aid}/descricao`, {method:'PUT',
      body: JSON.stringify({descricao: desc})});
    modalDescricaoBS.hide();
    toast('Descrição salva.');
    carregarDescricoes();
  } catch(e) { toast(e.message,'danger'); }
};

document.getElementById('descFiltroResp').onchange = () => {
  if (document.getElementById('tab-descricoes').classList.contains('active'))
    carregarDescricoes();
};

/* ── inicialização ───────────────────────────────── */
function recarregar() {
  atualizarMesLabel();
  carregarAtividades();
}

document.addEventListener('DOMContentLoaded', async () => {
  mesAtual = new Date();
  await carregarResponsaveis();
  recarregar();
});
