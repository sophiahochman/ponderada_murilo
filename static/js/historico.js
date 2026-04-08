/**
 * historico.js
 * Lógica do Frontend para a aba Histórico da Estação Meteorológica
 */

const API_BASE_URL = window.location.origin;
const PAGE_SIZE = 20;
let currentPageOffset = 0;

const elTableBody = document.getElementById('historico-body');
const elBtnNext = document.getElementById('btn-next');
const elBtnPrev = document.getElementById('btn-prev');
const elPageInfo = document.getElementById('page-info');
const elTotalRegisters = document.getElementById('total-registers');
const elBtnRefresh = document.getElementById('btn-refresh');

/**
 * Busca dados da API com suporte a paginação
 */
async function fetchHistorico() {
    try {
        const response = await fetch(`${API_BASE_URL}/leituras?limit=${PAGE_SIZE}&offset=${currentPageOffset}`, { cache: 'no-store' });
        if (!response.ok) throw new Error("Falha ao buscar histórico");
        
        const data = await response.json();
        renderTable(data.dados);
        updatePagination(data.paginacao);
    } catch (error) {
        console.error(error);
        elTableBody.innerHTML = '<tr><td colspan="7" class="text-center text-muted">Erro ao carregar dados.</td></tr>';
    }
}

/**
 * Renderiza as linhas da tabela
 */
function renderTable(leituras) {
    if (!leituras || leituras.length === 0) {
        elTableBody.innerHTML = '<tr><td colspan="7" class="text-center text-muted">Nenhum dado encontrado.</td></tr>';
        return;
    }

    const html = leituras.map(l => `
        <tr>
            <td style="color: var(--accent-purple); font-weight: 700;">#${l.id}</td>
            <td class="text-muted">${l.timestamp}</td>
            <td><span class="badge badge-table">${l.localizacao || 'N/A'}</span></td>
            <td style="color: var(--accent-orange); font-weight: 600;">${l.temperatura !== null ? l.temperatura.toFixed(2) : '--'} °C</td>
            <td style="color: var(--accent-blue); font-weight: 600;">${l.umidade !== null ? l.umidade.toFixed(2) : '--'} %</td>
            <td style="color: var(--accent-teal); font-weight: 600;">${l.pressao !== null ? l.pressao.toFixed(2) : '--'} hPa</td>
            <td class="text-center">
                <a href="/editar/${l.id}" class="btn btn-icon" style="display:inline-flex; width: 32px; height: 32px; color: var(--accent-blue);" title="Editar">
                    <i data-feather="edit" class="icon-small"></i>
                </a>
                <button class="btn btn-icon btn-delete" data-id="${l.id}" style="display:inline-flex; width: 32px; height: 32px; color: #ef4444;" title="Remover">
                    <i data-feather="trash-2" class="icon-small"></i>
                </button>
            </td>
        </tr>
    `).join('');
    
    elTableBody.innerHTML = html;
    
    // Atualizar Ícones dentro da tabela
    if(window.feather) feather.replace();

    // Atrelar eventos de Deleção
    document.querySelectorAll('.btn-delete').forEach(btn => {
        btn.addEventListener('click', handleDelete);
    });
}

/**
 * Deletar uma leitura
 */
async function handleDelete(e) {
    const btn = e.currentTarget;
    const id = btn.getAttribute('data-id');
    
    if(!confirm(`Tem certeza que deseja remover a leitura #${id}? Essa ação não pode ser desfeita.`)) {
        return;
    }

    // Efeito de loading no botão
    btn.innerHTML = '<i data-feather="loader" class="icon-small fa-spin"></i>';
    if(window.feather) feather.replace();
    
    try {
        const response = await fetch(`${API_BASE_URL}/leituras/${id}`, { method: 'DELETE' });
        if (response.ok) {
            // Remove a linha visualmente e recarrega a tabela atual
            fetchHistorico();
        } else {
            const err = await response.json();
            alert("Erro ao remover: " + (err.erro || "Desconhecido"));
        }
    } catch (error) {
        console.error(error);
        alert("Erro de conexão ao tentar deletar.");
    }
}

/**
 * Atualiza os controles de paginação
 */
function updatePagination(paginacao) {
    elBtnPrev.disabled = !paginacao.tem_anterior;
    elBtnNext.disabled = !paginacao.tem_proxima;
    elPageInfo.textContent = `Página ${paginacao.pagina_atual} de ${paginacao.total_paginas}`;
    elTotalRegisters.textContent = `Total: ${paginacao.total} registros`;
}

// Event Listeners
document.addEventListener('DOMContentLoaded', () => {
    fetchHistorico();
    
    elBtnNext.addEventListener('click', () => {
        currentPageOffset += PAGE_SIZE;
        fetchHistorico();
    });
    
    elBtnPrev.addEventListener('click', () => {
        currentPageOffset = Math.max(0, currentPageOffset - PAGE_SIZE);
        fetchHistorico();
    });
    
    elBtnRefresh.addEventListener('click', fetchHistorico);
});
