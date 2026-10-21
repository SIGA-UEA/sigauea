// Layout do DER em pé de galinha com o ELK (Eclipse Layout Kernel): posiciona as tabelas
// em camadas e roteia as linhas de forma ortogonal, desviando das caixas.
// Lê do stdin uma lista de grafos no formato do ELK e devolve no stdout os mesmos grafos
// com x/y das tabelas e os pontos de cada linha. Chamado por der_pe_de_galinha.py.
//
//   npm i --no-save elkjs@0.9.3     (uma vez; não altera o package.json)

import ELK from "elkjs/lib/elk.bundled.js";

const OPCOES = {
  "elk.algorithm": "layered",
  "elk.direction": "RIGHT",
  "elk.edgeRouting": "ORTHOGONAL",
  "elk.layered.crossingMinimization.strategy": "LAYER_SWEEP",
  "elk.layered.nodePlacement.strategy": "NETWORK_SIMPLEX",
  "elk.layered.spacing.nodeNodeBetweenLayers": "90",
  "elk.spacing.nodeNode": "36",
  "elk.spacing.edgeNode": "22",
  "elk.spacing.edgeEdge": "9",
  "elk.layered.spacing.edgeNodeBetweenLayers": "22",
  "elk.layered.spacing.edgeEdgeBetweenLayers": "9",
  "elk.edgeLabels.placement": "CENTER",
  "elk.layered.mergeEdges": "false",
  "elk.layered.thoroughness": "40",
  "elk.padding": "[top=70,left=40,bottom=40,right=40]",
};

let entrada = "";
for await (const parte of process.stdin) entrada += parte;
const grafos = JSON.parse(entrada);
const elk = new ELK();
const saida = [];
for (const g of grafos) {
  saida.push(await elk.layout({ ...g, layoutOptions: { ...OPCOES, ...(g.layoutOptions ?? {}) } }));
}
process.stdout.write(JSON.stringify(saida));
