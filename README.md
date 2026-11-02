# 🔄 Conversor de Arquivos

Extensão para Google Chrome desenvolvida para realizar conversões de arquivos localmente no computador.

O Conversor de Arquivos utiliza diferentes ferramentas de código aberto para processar áudio, vídeo, imagens, PDFs, documentos, planilhas e apresentações.

Os arquivos são processados localmente utilizando um programa Python conectado à extensão através do Native Messaging do Google Chrome.

---

## ✨ Principais recursos

- Seleção de arquivos diretamente do computador
- Detecção automática do tipo de arquivo
- Exibição apenas dos formatos de conversão compatíveis
- Escolha de qualidade quando aplicável
- Escolha da pasta de destino
- Conversão local
- Proteção contra sobrescrita de arquivos existentes
- Integração entre Chrome e Python usando Native Messaging
- Conversão de áudio e vídeo
- Conversão de imagens
- Conversão de PDFs
- Conversão de documentos
- Conversão de planilhas
- Conversão de apresentações
- OCR para extração de texto de imagens
- Interface simples para utilização do conversor

---

## 🧰 Tecnologias utilizadas

### Google Chrome Extension

A interface do conversor é executada como uma extensão baseada no Manifest V3.

### JavaScript

Responsável pela interface, validação das ações e comunicação com o Service Worker.

### Python

Responsável pelo programa local utilizado para executar as conversões.

### Native Messaging

Permite a comunicação entre a extensão do Chrome e o programa Python instalado no computador.

### FFmpeg e FFprobe

Utilizados para identificar e converter arquivos de áudio e vídeo.

### LibreOffice

Utilizado para conversões envolvendo documentos, planilhas e apresentações.

### Poppler

Utilizado para operações envolvendo PDF por meio das ferramentas `pdftotext`, `pdftoppm` e `pdftohtml`.

### ImageMagick

Utilizado para conversões entre formatos de imagem.

### Tesseract OCR

Utilizado para reconhecer texto existente em imagens.

### Zenity

Utilizado para abrir as janelas nativas de seleção de arquivos e pastas no Linux.

---

## 📁 Formatos suportados

### 🎵 Áudio

- MP3
- M4A
- AAC
- OGG
- OPUS
- WAV
- FLAC
- AC3
- AIFF
- WMA

Também é possível extrair áudio de arquivos de vídeo.

### 🎬 Vídeo

- MP4
- MKV
- WEBM
- MOV
- AVI
- MPEG
- WMV
- FLV
- GIF animado

### 🖼️ Imagens

Formatos reconhecidos incluem:

- JPG e JPEG
- PNG
- WEBP
- BMP
- GIF
- TIFF
- HEIC e HEIF
- AVIF
- JP2
- ICO
- TGA
- PSD

Também existe a opção de utilizar OCR para extrair texto da imagem.

### 📄 PDF

Arquivos PDF podem ser processados para:

- TXT
- HTML
- DOCX
- ODT
- PNG
- JPG
- TIFF

> A conversão de PDF para formatos editáveis pode apresentar diferenças de formatação dependendo da estrutura original do documento.

### 📝 Documentos

Formatos reconhecidos incluem:

- DOC
- DOCX
- ODT
- RTF
- WPS
- HTML
- EPUB

Possíveis formatos de saída incluem PDF, DOCX, DOC, ODT, RTF, TXT, HTML e EPUB.

### 📊 Planilhas

Formatos reconhecidos incluem:

- XLS
- XLSX
- ODS
- CSV
- TSV

Possíveis formatos de saída incluem PDF, XLSX, XLS, ODS, CSV e HTML.

### 📽️ Apresentações

Formatos reconhecidos incluem:

- PPT
- PPTX
- ODP

Possíveis formatos de saída incluem PDF, PPTX, PPT, ODP e PNG.

---

## 🔍 OCR

O projeto utiliza Tesseract OCR para extrair texto existente em imagens. Quando disponíveis no sistema, os idiomas português e inglês podem ser utilizados no reconhecimento.

---

## 🔒 Processamento local

A arquitetura foi desenvolvida para executar as conversões no próprio computador.

```text
Extensão Chrome
       │
       ▼
Service Worker
       │
       ▼
Native Messaging
       │
       ▼
converter_host.py
       │
       ├── FFmpeg
       ├── LibreOffice
       ├── Poppler
       ├── ImageMagick
       └── Tesseract
```

---

## 🔄 Fluxo de conversão

```text
Escolher arquivo
       ↓
Detectar o tipo
       ↓
Mostrar formatos compatíveis
       ↓
Escolher formato
       ↓
Escolher qualidade, quando aplicável
       ↓
Converter e salvar
       ↓
Escolher pasta de destino
       ↓
Executar conversão
       ↓
Arquivo convertido
```

---

## 📂 Estrutura do projeto

```text
conversor_de_arquivos/
│
├── manifest.json
├── README.md
├── .gitignore
│
├── assets/
│   └── icons/
│       ├── icon16.png
│       ├── icon48.png
│       └── icon128.png
│
├── background/
│   └── service-worker.js
│
├── popup/
│   ├── popup.html
│   ├── popup.css
│   └── popup.js
│
├── native-host/
│   ├── converter_host.py
│   └── install.sh
│
└── scripts/
    └── content.js
```

---

## ⚙️ Requisitos

O projeto foi desenvolvido e testado em ambiente Linux. São necessárias as seguintes ferramentas:

- Google Chrome
- Python 3
- FFmpeg e FFprobe
- LibreOffice
- Poppler
- ImageMagick
- Tesseract OCR
- Zenity

---

## 📦 Instalação das dependências

Em distribuições baseadas em Debian:

```bash
sudo apt update
sudo apt install -y \
  ffmpeg \
  libreoffice-writer \
  libreoffice-calc \
  libreoffice-impress \
  poppler-utils \
  imagemagick \
  tesseract-ocr \
  tesseract-ocr-por \
  zenity
```

---

## 🌐 Instalação da extensão

Clone o projeto:

```bash
git clone https://github.com/Bitze023/conversor_de_arquivos.git
```

Entre na pasta:

```bash
cd conversor_de_arquivos
```

Dê permissão ao programa Python:

```bash
chmod u+x native-host/converter_host.py
```

No Google Chrome:

1. Abra `chrome://extensions`.
2. Ative **Modo do desenvolvedor**.
3. Clique em **Carregar sem compactação**.
4. Selecione a pasta do projeto.

---

## 🔌 Configuração do Native Messaging

Depois de carregar a extensão, copie o ID exibido pelo Chrome e execute:

```bash
bash native-host/install.sh ID_DA_EXTENSAO
```

O script registra o host:

```text
com.mediadownloader.converter
```

---

## ▶️ Como usar

1. Clique no ícone do Conversor de Arquivos.
2. Clique em **Escolher arquivo do computador**.
3. Selecione o arquivo desejado.
4. Aguarde a identificação do tipo.
5. Escolha o formato de saída.
6. Escolha a qualidade quando essa opção estiver disponível.
7. Clique em **Converter e salvar**.
8. Escolha a pasta onde o arquivo será salvo.
9. Aguarde a mensagem de conclusão na janela do conversor.

---

## 🛡️ Segurança

O projeto utiliza algumas proteções importantes:

- validação das mensagens recebidas pela extensão;
- formatos de saída definidos pelo programa;
- comunicação por Native Messaging;
- execução dos conversores sem comandos de shell fornecidos pelo usuário;
- tokens temporários para identificar arquivos selecionados;
- arquivos existentes não são sobrescritos automaticamente;
- processamento realizado localmente.

---

## 🧪 Desenvolvimento

Validar os arquivos JavaScript:

```bash
node --check popup/popup.js
node --check background/service-worker.js
```

Validar o Python:

```bash
python3 -m py_compile native-host/converter_host.py
```

Validar o Manifest:

```bash
python3 -m json.tool manifest.json >/dev/null
```

---

## 🌳 Controle de versão

Depois de realizar alterações:

```bash
git status
git add .
git commit -m "Descricao da alteracao"
git push
```

---

## 👨‍💻 Autor

**Jose Diogo de Lima**

Projeto desenvolvido como estudo prático de:

- desenvolvimento de extensões Chrome;
- JavaScript;
- Python;
- Linux;
- FFmpeg;
- processamento de documentos e imagens;
- Native Messaging;
- Git e GitHub.

---

## 📌 Status

Projeto funcional em desenvolvimento contínuo. A arquitetura atual prioriza processamento local, interface simples e separação entre interface, comunicação e mecanismos de conversão.
