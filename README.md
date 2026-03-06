\# CIEC



\## Conversor de Imagens para Eleições Comunitárias



O \*\*CIEC\*\* é um aplicativo desenvolvido em Python para \*\*padronização, conversão e validação de imagens de candidatos\*\* utilizadas em eleições comunitárias (escolas, associações, sindicatos, etc.).



O sistema automatiza a preparação das imagens para importação em sistemas eleitorais, garantindo que todas estejam no \*\*formato correto, tamanho padronizado e com nomes compatíveis\*\*.



---



\# Principais funcionalidades



✔ Conversão automática de imagens para \*\*161 x 225 pixels\*\*

✔ Renomeação automática removendo acentos e caracteres especiais

✔ Geração automática do arquivo \*\*LISTA.TXT\*\*

✔ Registro de execução em \*\*arquivo de log\*\*

✔ Validação de imagens antes da importação

✔ Contagem automática de imagens na pasta

✔ Barra de progresso durante o processamento

✔ Interface gráfica simples e intuitiva



---



\# Interface do programa



A interface do CIEC possui os seguintes comandos:



| Botão               | Função                                                |

| ------------------- | ----------------------------------------------------- |

| \*\*Processar\*\*       | Converte e padroniza todas as imagens da pasta        |

| \*\*Parar\*\*           | Interrompe o processamento em andamento               |

| \*\*Validar imagens\*\* | Verifica se todas as imagens estão corretas           |

| \*\*Abrir saída\*\*     | Abre a pasta onde as imagens convertidas foram salvas |

| \*\*Ver Log\*\*         | Abre o arquivo de log da execução                     |

| \*\*Ajuda\*\*           | Exibe o manual do sistema                             |

| \*\*Sair\*\*            | Fecha o programa                                      |



---



\# Estrutura do projeto



```

CIEC

│

├─ src

│   └─ ciec

│       ├─ \_\_main\_\_.py

│       ├─ ciec\_gui.py

│       ├─ ui\_app.py

│       ├─ worker.py

│       └─ utils.py

│

├─ manual.pdf

├─ VERSION.txt

├─ README.md

└─ build.bat

```



---



\# Instalação



\## Executável (recomendado)



Basta executar:



```

CIEC.exe

```



Não requer instalação de Python.



---



\## Executar pelo Python



Requisitos:



\* Python 3.10+

\* Pillow



Instalar dependências:



```

pip install pillow

```



Executar:



```

python -m src.ciec

```



---



\# Como usar



1\. Abra o CIEC

2\. Selecione a pasta com as imagens dos candidatos

3\. Clique em \*\*Processar\*\*



O sistema irá:



\* converter as imagens

\* salvar na pasta `convertidos`

\* gerar `LISTA.TXT`

\* gerar o arquivo de log



Arquivos \*\*LISTA.TXT\*\* e \*\*logs\*\* são automaticamente \*\*ignorados nas validações\*\*.



---



\# Build do executável



Para gerar o executável:



```

pyinstaller --onefile --noconsole src/ciec/\_\_main\_\_.py

```



O executável será criado em:



```

dist/CIEC.exe

```



---



\# Licença



Este projeto é distribuído para uso interno e educacional.



---



\# Autor



Desenvolvido por \*\*Adailton Ventura\*\*



