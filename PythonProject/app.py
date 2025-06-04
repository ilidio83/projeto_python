import csv
import os
from flask import Flask, render_template, request, url_for, redirect
import requests
import json

app = Flask(__name__)


GEMINI_API_KEY = "AIzaSyDMFAT2g7p_epIRESYTq88Q2Vey-b4Vlkw"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"



def carregar_termos_glossario():
    """Carrega os termos do glossário do bd_glossario.csv como uma lista de dicionários."""
    termos = []
    caminho_arquivo = 'bd_glossario.csv'

    if not os.path.exists(caminho_arquivo):
        # Se o arquivo não existir, cria-o com o cabeçalho
        salvar_termos_glossario([])  # Cria o arquivo com cabeçalho
        return []

    with open(caminho_arquivo, newline='', encoding='utf-8') as arquivo:
        leitor = csv.DictReader(arquivo, delimiter=';')
        # Verifica se o leitor tem fieldnames (se o arquivo não está vazio sem cabeçalho)
        if leitor.fieldnames is None:
            # Arquivo vazio, retorna lista vazia
            return []

        for linha in leitor:
            # Converte o 'id' para inteiro, é importante para comparação
            if 'id' in linha and linha['id'].isdigit():
                linha['id'] = int(linha['id'])
            termos.append(linha)
    return termos


def salvar_termos_glossario(termos):
    """Salva uma lista de dicionários de termos no bd_glossario.csv."""
    caminho_arquivo = 'bd_glossario.csv'
    # Definir os nomes dos campos (cabeçalhos) explicitamente e na ordem correta
    fieldnames = ['id', 'termo', 'definicao']

    with open(caminho_arquivo, 'w', newline='', encoding='utf-8') as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=fieldnames, delimiter=';')
        escritor.writeheader()  # Escreve o cabeçalho
        escritor.writerows(termos)  # Escreve todas as linhas (dicionários)


def gerar_novo_id(termos):
    """Gera um novo ID único para um termo."""
    if not termos:
        return 1
    max_id = 0
    for t in termos:
        current_id = t.get('id')
        if isinstance(current_id, int):
            if current_id > max_id:
                max_id = current_id
        elif isinstance(current_id, str) and current_id.isdigit():
            if int(current_id) > max_id:
                max_id = int(current_id)
    return max_id + 1


# --- Rotas Flask ---

@app.route("/gemini", methods=["GET", "POST"])
def gemini():
    resposta_texto = ""
    if request.method == "POST":
        pergunta = request.form['pergunta']

        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": pergunta
                        }
                    ]
                }
            ]
        }

        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": GEMINI_API_KEY
        }

        try:
            response = requests.post(GEMINI_URL, json=payload, headers=headers, timeout=30)
            response.raise_for_status()  # Lança um HTTPError para códigos de status ruins (4xx ou 5xx)

            data = response.json()

            # Navegação segura para extrair o texto da resposta
            resposta_texto = (
                data.get("candidates", [{}])[0]
                .get("content", {})
                .get("parts", [{}])[0]
                .get("text", "Sem resposta.")
            )
        except requests.exceptions.RequestException as e:
            resposta_texto = f"Erro de conexão ou da API: '{str(e)}'"
        except json.JSONDecodeError:
            resposta_texto = "Erro ao decodificar a resposta JSON da API."
        except Exception as e:
            resposta_texto = f"Erro inesperado: '{str(e)}'"

    return render_template("gemini.html", Resposta=resposta_texto)


@app.route('/')
def index():
    glossario_de_termos = carregar_termos_glossario()
    return render_template('index.html', glossario_de_termos=glossario_de_termos)


@app.route('/fundamentos_python')
def fundamentos_python():
    return render_template('fundamentos_python.html')


@app.route('/sobre-equipe')
def sobre_equipe():
    return render_template('sobre.html')


@app.route('/glossario')
def glossario():
    glossario_de_termos = carregar_termos_glossario()
    return render_template('glossario.html', glossario=glossario_de_termos)


@app.route('/novo_termo')
def novo_termo():
    return render_template('novo_termo.html')


@app.route('/criar_termo', methods=['POST', ])
def criar_termo():
    termo = request.form['termo']
    definicao = request.form['definicao']

    termos_existentes = carregar_termos_glossario()
    novo_id = gerar_novo_id(termos_existentes)

    novo_item = {'id': novo_id, 'termo': termo, 'definicao': definicao}
    termos_existentes.append(novo_item)

    salvar_termos_glossario(termos_existentes)

    return redirect(url_for('glossario'))


@app.route('/alterar_termo/<int:termo_id>', methods=['GET', 'POST'])
def alterar_termo(termo_id):
    glossario_data = carregar_termos_glossario()
    termo_a_editar = None

    for termo in glossario_data:
        if termo.get('id') == termo_id:
            termo_a_editar = termo
            break

    if termo_a_editar is None:
        return "Termo não encontrado!", 404

    if request.method == 'POST':
        termo_atualizado_valor = request.form['termo']
        definicao_atualizada_valor = request.form['definicao']

        termo_a_editar['termo'] = termo_atualizado_valor
        termo_a_editar['definicao'] = definicao_atualizada_valor

        salvar_termos_glossario(glossario_data)

        return redirect(url_for('glossario'))

    return render_template('alterar_termo.html', termo=termo_a_editar)


# NOVO: Rota para apagar termo
@app.route('/apagar_termo/<int:termo_id>', methods=['GET'])  # Usando GET para simplicidade com o link
def apagar_termo(termo_id):
    glossario_data = carregar_termos_glossario()

    # Cria uma nova lista contendo todos os termos EXCETO o termo com o ID a ser apagado
    # Isso é mais seguro do que remover enquanto itera sobre a lista original
    nova_lista_termos = [termo for termo in glossario_data if termo.get('id') != termo_id]

    if len(nova_lista_termos) == len(glossario_data):
        # Se os tamanhos são iguais, significa que nenhum termo foi removido (ID não encontrado)
        return "Termo não encontrado para apagar.", 404

    salvar_termos_glossario(nova_lista_termos)

    return redirect(url_for('glossario'))


if __name__ == '__main__':
    app.run(debug=True)