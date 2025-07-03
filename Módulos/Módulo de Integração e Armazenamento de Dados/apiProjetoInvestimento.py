import requests

idUnico = "21460.43-31"

url = "https://api.obrasgov.gestao.gov.br/obrasgov/api/projeto-investimento"

params = {
    "idUnico": idUnico,
    "pagina": 0,
    "tamanhoDaPagina": 10
}

headers = {
    "accept": "*/*"
}

response = requests.get(url, params=params, headers=headers)


if response.status_code == 200:
    dados = response.json()
    
    for item in dados.get("content", []):
        print(f"Id Único: {item.get('idUnico', 'N/A')}")
        print(f"Nome: {item.get('nome', 'N/A')}")
        print(f"CEP: {item.get('cep', 'N/A')}")
        print(f"Endereço: {item.get('endereco', 'N/A')}")
        print(f"Descrição: {item.get('descricao', 'N/A')}")
        print(f"Função Social: {item.get('funcaoSocial', 'N/A')}")
        print(f"Meta Global: {item.get('metaGlobal', 'N/A')}")
        print(f"Data Inicial Prevista: {item.get('dataInicialPrevista', 'N/A')}")
        print(f"Data Final Prevista: {item.get('dataFinalPrevista', 'N/A')}")
        print(f"Data Inicial Efetiva: {item.get('dataInicialEfetiva', 'N/A')}")
        print(f"Data Final Efetiva: {item.get('dataFinalEfetiva', 'N/A')}")
        print(f"Data Cadastro: {item.get('dataCadastro', 'N/A')}")
        print(f"Especie: {item.get('especie', 'N/A')}")
        print(f"Natureza: {item.get('natureza', 'N/A')}")
        print(f"Natureza Outras: {item.get('naturezaOutras', 'N/A')}")
        print(f"Situação: {item.get('situacao', 'N/A')}")
        print(f"Desc Plano Nacional Politica Vinculado: {item.get('descPlanoNacionalPoliticaVinculado', 'N/A')}")
        print(f"UF: {item.get('uf', 'N/A')}")
        print(f"Qdt Empregos Gerados: {item.get('qdtEmpregosGerados', 'N/A')}")
        print(f"Desc População Beneficiada: {item.get('descPopulacaoBeneficiada', 'N/A')}")
        print(f"População Beneficiada: {item.get('populacaoBeneficiada', 'N/A')}")
        print(f"Observações Pertinentes: {item.get('observacoesPertinentes', 'N/A')}")
        print(f"isModeladaPorBim: {item.get('isModeladaPorBim', 'N/A')}")
        print(f"Data Situação: {item.get('dataSituacao', 'N/A')}")
        print(f"Tomadores: {item.get('tomadores', 'N/A')}")
        print(f"Executores: {item.get('executores', 'N/A')}")
        print(f"Repassadores: {item.get('repassadores', 'N/A')}")
        print(f"Eixos: {item.get('eixos', 'N/A')}")
        print(f"Tipos: {item.get('tipos', 'N/A')}")
        print(f"subTipos: {item.get('subtipos', 'N/A')}")
        print(f"geometrias: {item.get('geometrias', 'N/A')}")
        print(f"fontesDeRecurso: {item.get('fontesDeRecurso', 'N/A')}")
        print("-" * 40)
else:
    print(f"Erro {response.status_code}: {response.text}")
