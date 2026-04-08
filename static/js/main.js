/**
 * main.js
 * Lógica do Frontend para o Dashboard da Estação Meteorológica
 */

const API_BASE_URL = window.location.origin; // O front e o back estão no mesmo servidor
const REFRESH_INTERVAL_MS = 5000; // 5 segundos

// Elementos da DOM
const elCurrentTemp = document.getElementById('current-temp');
const elMinTemp = document.getElementById('min-temp');
const elMaxTemp = document.getElementById('max-temp');
const elAvgTemp = document.getElementById('avg-temp');

const elCurrentUmid = document.getElementById('current-umid');
const elMinUmid = document.getElementById('min-umid');
const elMaxUmid = document.getElementById('max-umid');
const elAvgUmid = document.getElementById('avg-umid');

const elCurrentPress = document.getElementById('current-press');
const elMinPress = document.getElementById('min-press');
const elMaxPress = document.getElementById('max-press');
const elAvgPress = document.getElementById('avg-press');

const elTotalLeituras = document.getElementById('total-leituras');
const elBtnRefresh = document.getElementById('btn-refresh');
const elTableBody = document.getElementById('table-body');
const elStatusIndicator = document.querySelector('.status-indicator');
const elClock = document.getElementById('clock-display');

// Gráfico (Chart.js)
let historyChart = null;
let lastKnownId = null;

/**
 * Atualiza o relógio no header
 */
function updateClock() {
    const now = new Date();
    elClock.textContent = now.toLocaleTimeString('pt-BR', {
        hour12: false,
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
}
setInterval(updateClock, 1000);
updateClock();

/**
 * Anima as mudanças numéricas para dar um feedback visual
 */
function animateValueUpdate(element, newValue, suffix = '') {
    const currentText = element.textContent.replace(suffix, '').trim();
    if (currentText !== newValue.toString()) {
        element.textContent = newValue + suffix;
        element.classList.remove('highlight-update');
        void element.offsetWidth; // Trigger reflow
        element.classList.add('highlight-update');
    }
}

/**
 * Inicializa o Chart.js
 */
function initChart() {
    const ctx = document.getElementById('historyChart').getContext('2d');
    
    // Configurações Globais do Chart.js para Light Mode / Bento Theme
    Chart.defaults.color = '#6b7280';
    Chart.defaults.font.family = "'Outfit', sans-serif";
    
    historyChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [], // Timestamps
            datasets: [
                {
                    label: 'Temperatura (°C)',
                    borderColor: '#f97316',
                    backgroundColor: 'rgba(249, 115, 22, 0.15)',
                    borderWidth: 3,
                    pointBackgroundColor: '#f97316',
                    pointBorderColor: '#ffffff',
                    pointRadius: 4,
                    pointHoverRadius: 6,
                    tension: 0.4, // Curva suave
                    fill: true,
                    data: [],
                    yAxisID: 'y'
                },
                {
                    label: 'Umidade (%)',
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59, 130, 246, 0.15)',
                    borderWidth: 3,
                    pointBackgroundColor: '#3b82f6',
                    pointBorderColor: '#ffffff',
                    pointRadius: 4,
                    pointHoverRadius: 6,
                    tension: 0.4,
                    fill: true,
                    data: [],
                    yAxisID: 'y1'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false,
            },
            plugins: {
                tooltip: {
                    backgroundColor: 'rgba(255, 255, 255, 0.95)',
                    titleColor: '#111827',
                    bodyColor: '#374151',
                    borderColor: 'rgba(0, 0, 0, 0.05)',
                    borderWidth: 1,
                    padding: 14,
                    boxPadding: 8,
                    usePointStyle: true,
                    titleFont: { size: 14, family: "'Outfit', sans-serif", weight: 'bold' },
                    bodyFont: { size: 13, family: "'Outfit', sans-serif" }
                },
                legend: {
                    display: false // Usamos as badges customizadas em HTML em vez da legenda
                }
            },
            scales: {
                x: {
                    grid: {
                        display: false,
                        drawBorder: false,
                    },
                    ticks: {
                        maxTicksLimit: 8
                    }
                },
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    grid: {
                        color: 'rgba(0, 0, 0, 0.03)',
                        drawBorder: false,
                    },
                    title: {
                        display: true,
                        text: 'Temperatura (°C)',
                        color: '#f97316',
                        font: { size: 12, weight: 600, family: "'Outfit', sans-serif" }
                    }
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    grid: {
                        drawOnChartArea: false, // Só desenha as linhas da grid Y principal
                    },
                    title: {
                        display: true,
                        text: 'Umidade (%)',
                        color: '#3b82f6',
                        font: { size: 12, weight: 600, family: "'Outfit', sans-serif" }
                    }
                }
            }
        }
    });
}

/**
 * Atualiza os dados no Chart.js
 */
function updateChartData(leituras) {
    if (!historyChart) return;
    
    // Pegamos até 24 leituras e invertemos para ordem cronológica (esq -> dir)
    const dadosGrafico = [...leituras].slice(0, 24).reverse();
    
    const labels = dadosGrafico.map(l => {
        const d = new Date(l.timestamp);
        return d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    });
    
    const dataTemp = dadosGrafico.map(l => l.temperatura);
    const dataUmid = dadosGrafico.map(l => l.umidade);
    
    historyChart.data.labels = labels;
    historyChart.data.datasets[0].data = dataTemp;
    historyChart.data.datasets[1].data = dataUmid;
    
    historyChart.update('none'); // Update sem animação completa para não saltar muito no polling
}

/**
 * Atualiza a Tabela HTML com as últimas 10 leituras
 */
function updateTableData(leituras) {
    if (leituras.length === 0) {
        elTableBody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">Nenhum dado registrado.</td></tr>';
        return;
    }

    const html = leituras.slice(0, 10).map((l, index) => {
        // Se for uma leitura novinha (id maior que a última conhecida), a gente pisca a linha
        const isNew = lastKnownId !== null && l.id > lastKnownId;
        const rowClass = isNew ? 'class="highlight-row"' : '';
        
        return `
            <tr ${rowClass}>
                <td style="color: var(--accent-purple); font-weight: 700;">#${l.id}</td>
                <td class="text-muted">${l.timestamp}</td>
                <td><span class="badge badge-table">${l.localizacao || 'N/A'}</span></td>
                <td style="color: var(--accent-orange); font-weight: 600;">${l.temperatura !== null ? l.temperatura.toFixed(2) : '--'} °C</td>
                <td style="color: var(--accent-blue); font-weight: 600;">${l.umidade !== null ? l.umidade.toFixed(2) : '--'} %</td>
                <td style="color: var(--accent-teal); font-weight: 600;">${l.pressao !== null ? l.pressao.toFixed(2) : '--'} hPa</td>
            </tr>
        `;
    }).join('');
    
    elTableBody.innerHTML = html;
    
    // Atualiza o lastKnownId apos renderizar
    if (leituras.length > 0) {
        lastKnownId = leituras[0].id; // A primeira é a mais recente porque vem desc
    }
}

/**
 * Atualiza os cartões superiores (Médias e Totais) e o atual
 */
function updateStatsAndCurrent(estatisticas, ultimaLeitura) {
    // 1. Atualizar Atual (usando a ultima leitura real e não estatisticas globais pro número principal)
    if (ultimaLeitura) {
        animateValueUpdate(elCurrentTemp, ultimaLeitura.temperatura ? ultimaLeitura.temperatura.toFixed(1) : '--');
        animateValueUpdate(elCurrentUmid, ultimaLeitura.umidade ? ultimaLeitura.umidade.toFixed(1) : '--');
        animateValueUpdate(elCurrentPress, ultimaLeitura.pressao ? ultimaLeitura.pressao.toFixed(1) : '--');
    }
    
    if (estatisticas) {
        // 2. Estatísticas Temperatura
        elMinTemp.textContent = estatisticas.temperatura.min.toFixed(1);
        elMaxTemp.textContent = estatisticas.temperatura.max.toFixed(1);
        elAvgTemp.textContent = estatisticas.temperatura.media.toFixed(1);
        
        // 3. Estatísticas Umidade
        elMinUmid.textContent = estatisticas.umidade.min.toFixed(1);
        elMaxUmid.textContent = estatisticas.umidade.max.toFixed(1);
        elAvgUmid.textContent = estatisticas.umidade.media.toFixed(1);
        
        // 4. Estatísticas Pressão
        elMinPress.textContent = estatisticas.pressao.min ? estatisticas.pressao.min.toFixed(1) : '--';
        elMaxPress.textContent = estatisticas.pressao.max ? estatisticas.pressao.max.toFixed(1) : '--';
        elAvgPress.textContent = estatisticas.pressao.media ? estatisticas.pressao.media.toFixed(1) : '--';
        
        // 5. Total
        animateValueUpdate(elTotalLeituras, estatisticas.total_leituras);
    }
}

/**
 * Faz fetch dos dados da API
 */
async function fetchData() {
    try {
        // Mostra indicativo de atividade (pisca a bolinha verde)
        elStatusIndicator.style.backgroundColor = '#14b8a6'; 
        
        // Dispara requisições paralelas para /leituras (histórico) e /api/estatisticas
        const [resLeituras, resEstatisticas] = await Promise.all([
            fetch(`${API_BASE_URL}/leituras?limit=24`, { cache: 'no-store' }),
            fetch(`${API_BASE_URL}/api/estatisticas`, { cache: 'no-store' })
        ]);

        if (!resLeituras.ok) throw new Error(`Falha no GET /leituras: ${resLeituras.status}`);
        
        const dataLeituras = await resLeituras.json();
        
        let dataEstatisticas = null;
        if (resEstatisticas.ok) {
            dataEstatisticas = await resEstatisticas.json();
        }

        const leituras = dataLeituras.dados || [];
        const ultimaLeitura = leituras.length > 0 ? leituras[0] : null;

        // Propaga dados para UI
        updateTableData(leituras);
        updateChartData(leituras);
        updateStatsAndCurrent(dataEstatisticas, ultimaLeitura);
        
        // Reseta cor da bolinha após sucesso
        setTimeout(() => elStatusIndicator.style.backgroundColor = '', 500);

    } catch (error) {
        console.error('Erro ao buscar dados na API:', error);
        // Indicativo de erro
        elStatusIndicator.style.backgroundColor = '#ef4444'; // Vermelho
        elStatusIndicator.style.boxShadow = '0 0 10px #ef4444';
    }
}

/**
 * Inicialização
 */
document.addEventListener('DOMContentLoaded', () => {
    initChart();
    fetchData(); // Chama logo de cara
    
    // Inicia polling (verificação cíclica)
    setInterval(fetchData, REFRESH_INTERVAL_MS);
    
    // Ação no botão de Recarregar Manualmente
    if(elBtnRefresh) {
        elBtnRefresh.addEventListener('click', () => {
            elBtnRefresh.querySelector('i').classList.add('fa-spin'); // placeholder pra animacao css
            fetchData().finally(() => {
                setTimeout(()=> elBtnRefresh.querySelector('i').classList.remove('fa-spin'), 300);
            });
        });
    }
});
