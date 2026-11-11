# GNZ01_ — Cinematic Brand Introduction (prompt oficial do João)

Este é o prompt definitivo da identidade dos vídeos do @gnz01_. Ele substitui a versão laranja (AR FILMAGENS), que foi cancelada.

- 12 s no prompt original; por pedido do João, os vídeos publicados têm sempre 30 s e todo texto em português. Master em 1080×1080 com timeline a 29,97 fps e saída a 59,94 fps, H.264. Para Reels: 1080×1920.
- Paleta: #08090B, #111318, #202227, #34363C, #F4F2ED e destaque em dourado discreto #C5A46D.
- Proibido usar roxo, magenta, laranja ou azul forte.
- Tipografia Inter.
- Oito cenas:
  1. revelação da marca GNZ01_ sobre um navegador desfocado, com anel e clique;
  2. símbolo 3D com órbitas que travam;
  3. desktop com prompt de vidro e digitação;
  4. site rolando, com destaque dourado;
  5. card de Web Development;
  6. cards Websites e Systems;
  7. símbolo metálico com reflexo;
  8. assinatura "GNZ01_ / DESIGN. DESENVOLVIMENTO. DIGITAL.".
- Áudio: eletrônica premium a 124 BPM com efeitos sincronizados e sem narração, em -14 LUFS e true peak de -1 dBTP.
- Produção: uma página HTML com renderização determinística, sem Math.random e sem timers. Os quadros são capturados com Playwright e codificados com FFmpeg.

Implementação em `tools/filme_marca/`:

```
python3 tools/filme_marca/trilha.py trilha.wav 30
node tools/filme_marca/render.js saida.mp4 --w 1080 --h 1920 --fps 59.94 --audio trilha.wav --dur 30
```

Os Reels diários (`src/reels.py`) seguem a mesma identidade: fundo escuro, Inter, destaques em dourado `OURO` e assinatura final "GNZ01_ / DESIGN. DESENVOLVIMENTO. DIGITAL.".
