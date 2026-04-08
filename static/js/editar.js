/**
 * editar.js
 * Lógica do Frontend para pré-carregar os dados de uma leitura e salvá-los
 */

const API_BASE_URL = window.location.origin;
const form = document.getElementById('edit-form');
const feedback = document.getElementById('form-feedback');
const btnSave = document.getElementById('btn-save');

const idLeitura = form.getAttribute('data-id');

// Inputs
const inputTemp = document.getElementById('temperatura');
const inputUmid = document.getElementById('umidade');
const inputPress = document.getElementById('pressao');
const inputLoc = document.getElementById('localizacao');

/**
 * Função para exibir mensagens de sucesso ou erro
 */
function showMessage(type, message) {
    feedback.className = `feedback ${type}`;
    feedback.textContent = message;
}

/**
 * Faz fetch dos dados da API para preencher os inputs inicialmente
 */
async function loadData() {
    try {
        const response = await fetch(`${API_BASE_URL}/leituras/${idLeitura}`);
        if (!response.ok) throw new Error("Leitura não encontrada.");
        
        const data = await response.json();
        const l = data.dados;
        
        inputTemp.value = l.temperatura;
        inputUmid.value = l.umidade;
        
        if(l.pressao !== null) inputPress.value = l.pressao;
        if(l.localizacao) inputLoc.value = l.localizacao;
        
    } catch (error) {
        console.error(error);
        showMessage('error', 'Não foi possível carregar os dados desta leitura. Ela pode ter sido deletada.');
        btnSave.disabled = true;
    }
}

/**
 * Envia o PUT com os dados alterados
 */
async function saveData(e) {
    e.preventDefault();
    
    // Mostra loading no botão
    const originalBtnText = btnSave.innerHTML;
    btnSave.innerHTML = '<i data-feather="loader" class="fa-spin icon-small"></i> Salvando...';
    btnSave.disabled = true;
    if(window.feather) feather.replace();
    
    // Constrói payload
    const payload = {
        temperatura: parseFloat(inputTemp.value),
        umidade: parseFloat(inputUmid.value),
    };
    
    if(inputPress.value) payload.pressao = parseFloat(inputPress.value);
    if(inputLoc.value) payload.localizacao = inputLoc.value;
    
    try {
        const response = await fetch(`${API_BASE_URL}/leituras/${idLeitura}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });
        
        const jsonResponse = await response.json();
        
        if (response.ok) {
            showMessage('success', '✅ Leitura atualizada com sucesso!');
        } else {
            showMessage('error', 'Erro: ' + (jsonResponse.erro || 'Falha na validação dos dados.'));
        }
    } catch (error) {
        console.error(error);
        showMessage('error', 'Erro crítico de rede.');
    } finally {
        btnSave.innerHTML = originalBtnText;
        btnSave.disabled = false;
        if(window.feather) feather.replace();
    }
}

document.addEventListener('DOMContentLoaded', () => {
    loadData();
    form.addEventListener('submit', saveData);
});
