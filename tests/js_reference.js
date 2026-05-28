// js_reference.js
//
// This file extracts the canonical scoring engine from index.html (the
// public CVM tool) and exposes it as a Node.js module for use by the
// Python parity tests.
//
// HOW THE PARITY HARNESS USES IT:
//   1. cvm_research/scoring.py implements compute_dimensions in Python
//   2. tests/test_parity.py invokes this JS file via subprocess
//   3. Both score the same set of test cases
//   4. Test fails if any dimension differs by more than ±1 point
//
// The JS engine here is COPIED FROM index.html — keep them in sync.
// If you change one, run the parity test before committing.

const SECTOR_BASELINES = {
  TECH:   { fundamentals:{pe:32,pb:6.5,currentRatio:2.4,epsCagr:14,divYield:0.6,shareholderYield:1.5,debtEquity:0.4}, dims:{financial_metrics:62,financial_engineering:70,tech_adoption:88,strategic_transformation:78,management_stake:72,ownership_structure:65,culture_purpose:75,progressive_practices:80,macro_environment:60,market_dynamics:65} },
  FIN:    { fundamentals:{pe:12,pb:1.4,currentRatio:null,epsCagr:7,divYield:3.2,shareholderYield:5.5,debtEquity:null}, dims:{financial_metrics:70,financial_engineering:62,tech_adoption:55,strategic_transformation:55,management_stake:60,ownership_structure:62,culture_purpose:55,progressive_practices:55,macro_environment:50,market_dynamics:55} },
  HC:     { fundamentals:{pe:24,pb:4.2,currentRatio:1.9,epsCagr:9,divYield:1.8,shareholderYield:3.0,debtEquity:0.6}, dims:{financial_metrics:72,financial_engineering:68,tech_adoption:62,strategic_transformation:62,management_stake:58,ownership_structure:60,culture_purpose:70,progressive_practices:65,macro_environment:72,market_dynamics:60} },
  CONS_C: { fundamentals:{pe:22,pb:4.0,currentRatio:1.4,epsCagr:8,divYield:1.4,shareholderYield:2.8,debtEquity:0.7}, dims:{financial_metrics:60,financial_engineering:62,tech_adoption:60,strategic_transformation:62,management_stake:55,ownership_structure:55,culture_purpose:62,progressive_practices:60,macro_environment:50,market_dynamics:55} },
  CONS_D: { fundamentals:{pe:21,pb:5.5,currentRatio:1.2,epsCagr:6,divYield:2.6,shareholderYield:4.5,debtEquity:0.8}, dims:{financial_metrics:75,financial_engineering:70,tech_adoption:55,strategic_transformation:55,management_stake:55,ownership_structure:60,culture_purpose:68,progressive_practices:58,macro_environment:75,market_dynamics:55} },
  ENERGY: { fundamentals:{pe:11,pb:1.8,currentRatio:1.4,epsCagr:5,divYield:4.0,shareholderYield:7.0,debtEquity:0.5}, dims:{financial_metrics:62,financial_engineering:60,tech_adoption:48,strategic_transformation:50,management_stake:55,ownership_structure:55,culture_purpose:50,progressive_practices:48,macro_environment:45,market_dynamics:55} },
  INDUS:  { fundamentals:{pe:20,pb:3.6,currentRatio:1.7,epsCagr:7,divYield:1.8,shareholderYield:3.2,debtEquity:0.7}, dims:{financial_metrics:65,financial_engineering:65,tech_adoption:60,strategic_transformation:60,management_stake:58,ownership_structure:60,culture_purpose:60,progressive_practices:60,macro_environment:60,market_dynamics:55} },
  MAT:    { fundamentals:{pe:15,pb:2.4,currentRatio:1.7,epsCagr:5,divYield:2.5,shareholderYield:4.0,debtEquity:0.6}, dims:{financial_metrics:62,financial_engineering:58,tech_adoption:50,strategic_transformation:55,management_stake:55,ownership_structure:55,culture_purpose:55,progressive_practices:52,macro_environment:50,market_dynamics:55} },
  COMM:   { fundamentals:{pe:23,pb:3.8,currentRatio:1.3,epsCagr:8,divYield:2.0,shareholderYield:3.5,debtEquity:1.1}, dims:{financial_metrics:60,financial_engineering:62,tech_adoption:75,strategic_transformation:65,management_stake:62,ownership_structure:58,culture_purpose:62,progressive_practices:65,macro_environment:60,market_dynamics:60} },
  UTIL:   { fundamentals:{pe:18,pb:1.9,currentRatio:1.0,epsCagr:4,divYield:3.6,shareholderYield:3.8,debtEquity:1.4}, dims:{financial_metrics:68,financial_engineering:60,tech_adoption:50,strategic_transformation:50,management_stake:52,ownership_structure:55,culture_purpose:60,progressive_practices:55,macro_environment:75,market_dynamics:50} },
  RE:     { fundamentals:{pe:30,pb:2.1,currentRatio:1.1,epsCagr:5,divYield:4.2,shareholderYield:4.5,debtEquity:1.2}, dims:{financial_metrics:62,financial_engineering:60,tech_adoption:50,strategic_transformation:55,management_stake:58,ownership_structure:60,culture_purpose:58,progressive_practices:55,macro_environment:55,market_dynamics:50} },
  ETF:    { fundamentals:{pe:18,pb:2.5,currentRatio:null,epsCagr:6,divYield:2.0,shareholderYield:2.0,debtEquity:null}, dims:{financial_metrics:65,financial_engineering:65,tech_adoption:60,strategic_transformation:60,management_stake:50,ownership_structure:60,culture_purpose:60,progressive_practices:60,macro_environment:60,market_dynamics:60} }
};

const CAP_ADJ = {
  M: { financial_metrics:+8, financial_engineering:+5, tech_adoption:+3, strategic_transformation:-2, management_stake:-5, market_dynamics:-3 },
  L: { financial_metrics:+3, financial_engineering:+2 },
  I: { financial_metrics:-2, strategic_transformation:+5, tech_adoption:+2, market_dynamics:+3 },
  S: { financial_metrics:-8, strategic_transformation:+8, tech_adoption:+3, management_stake:+8, market_dynamics:+5 }
};

const COUNTRY_ADJ = {
  US:{ ownership_structure:+3, management_stake:+2 },
  GB:{ ownership_structure:+3 },
  DE:{ ownership_structure:+2, culture_purpose:+2 },
  FR:{ ownership_structure:+2 },
  NL:{ ownership_structure:+3 },
  CH:{ ownership_structure:+3, financial_engineering:+3 },
  CA:{ ownership_structure:+2 },
  AU:{ ownership_structure:+2 },
  JP:{ ownership_structure:-2, progressive_practices:-3, culture_purpose:+3 },
  KR:{ ownership_structure:-5, management_stake:-3 },
  CN:{ ownership_structure:-10, management_stake:-5, macro_environment:-5 },
  HK:{ ownership_structure:-3, macro_environment:-3 },
  TW:{ ownership_structure:-2, macro_environment:-3 },
  IN:{ ownership_structure:-5, management_stake:-3, strategic_transformation:+3 },
  BR:{ ownership_structure:-7, macro_environment:-6 },
  MX:{ ownership_structure:-5, macro_environment:-4 },
  ZA:{ ownership_structure:-5, macro_environment:-5 },
  TR:{ ownership_structure:-7, macro_environment:-8 },
  ID:{ ownership_structure:-6, macro_environment:-4 },
  TH:{ ownership_structure:-4, macro_environment:-3 },
  SG:{ ownership_structure:+2 },
  SA:{ ownership_structure:-8, macro_environment:-3 },
  AE:{ ownership_structure:-5 },
  EU:{ ownership_structure:+2 },
  EM:{ ownership_structure:-5, macro_environment:-5 }
};

const LAYERS = [
  { id:'macro',   weight:0.10, dimensions:['macro_environment'] },
  { id:'finarch', weight:0.20, dimensions:['financial_metrics','financial_engineering'] },
  { id:'corp',    weight:0.22, dimensions:['tech_adoption','strategic_transformation'] },
  { id:'gov',     weight:0.25, dimensions:['management_stake','ownership_structure'] },
  { id:'org',     weight:0.18, dimensions:['culture_purpose','progressive_practices'] },
  { id:'opt',     weight:0.05, dimensions:['market_dynamics'] }
];

function clamp(n, lo, hi) { return Math.max(lo, Math.min(hi, n)); }

function fnv1a(str) {
  let h = 0x811c9dc5;
  for (let i = 0; i < str.length; i++) {
    h ^= str.charCodeAt(i);
    h = (h * 0x01000193) >>> 0;
  }
  return h >>> 0;
}

function tickerVariance(ticker, dimId, range) {
  const seed = fnv1a((ticker + ':' + dimId).toLowerCase());
  const r = (seed % 10000) / 10000;
  return Math.round((r - 0.5) * 2 * range);
}

function computeDimensions(stock, fundamentals) {
  const sec = SECTOR_BASELINES[stock.sector] || SECTOR_BASELINES.INDUS;
  const dims = Object.assign({}, sec.dims);
  const capAdj = CAP_ADJ[stock.cap] || {};
  for (const k in capAdj) if (dims[k] !== undefined) dims[k] = clamp(dims[k] + capAdj[k], 0, 100);
  const ctyAdj = COUNTRY_ADJ[stock.country] || {};
  for (const k in ctyAdj) if (dims[k] !== undefined) dims[k] = clamp(dims[k] + ctyAdj[k], 0, 100);
  const hasLive = fundamentals && fundamentals.source !== 'demo';
  const varRange = hasLive ? 2 : 6;
  for (const k in dims) {
    dims[k] = clamp(dims[k] + tickerVariance(stock.ticker, k, varRange), 0, 100);
  }
  const dataDriven = {};
  if (hasLive) {
    const sb = sec.fundamentals;
    const secId = stock.sector;
    if (fundamentals.pe != null && sb.pe) {
      const peDelta = (sb.pe - fundamentals.pe) / sb.pe;
      dims.financial_metrics = clamp(dims.financial_metrics + Math.round(peDelta * 14), 0, 100);
      dataDriven.financial_metrics = true;
    }
    if (fundamentals.pb != null && sb.pb) {
      const pbDelta = (sb.pb - fundamentals.pb) / sb.pb;
      dims.financial_metrics = clamp(dims.financial_metrics + Math.round(pbDelta * 8), 0, 100);
      dataDriven.financial_metrics = true;
    }
    if (fundamentals.currentRatio != null && sb.currentRatio) {
      const crDelta = (fundamentals.currentRatio - sb.currentRatio) / sb.currentRatio;
      dims.financial_metrics = clamp(dims.financial_metrics + Math.round(crDelta * 6), 0, 100);
      dataDriven.financial_metrics = true;
    }
    if (fundamentals.operatingMargin != null) {
      const omAnchor = secId === 'TECH' ? 25 : secId === 'FIN' ? 30 : secId === 'CONS_D' ? 12 : 15;
      const omDelta = (fundamentals.operatingMargin - omAnchor) / omAnchor;
      dims.financial_metrics = clamp(dims.financial_metrics + Math.round(omDelta * 6), 0, 100);
      dataDriven.financial_metrics = true;
    }
    if (fundamentals.shareholderYield != null && sb.shareholderYield) {
      const syDelta = (fundamentals.shareholderYield - sb.shareholderYield) / Math.max(0.5, sb.shareholderYield);
      dims.financial_engineering = clamp(dims.financial_engineering + Math.round(syDelta * 8), 0, 100);
      dataDriven.financial_engineering = true;
    }
    if (fundamentals.roe != null) {
      const roeAnchor = secId === 'TECH' ? 20 : secId === 'FIN' ? 12 : secId === 'UTIL' ? 10 : 15;
      const roeDelta = (fundamentals.roe - roeAnchor) / Math.max(5, roeAnchor);
      dims.financial_engineering = clamp(dims.financial_engineering + Math.round(roeDelta * 8), 0, 100);
      dataDriven.financial_engineering = true;
    }
    if (fundamentals.debtEquity != null) {
      const deAnchor = secId === 'FIN' ? 1.5 : secId === 'UTIL' ? 1.4 : secId === 'RE' ? 1.2 : 0.6;
      const deDelta = (deAnchor - fundamentals.debtEquity) / Math.max(0.3, deAnchor);
      dims.financial_engineering = clamp(dims.financial_engineering + Math.round(deDelta * 6), 0, 100);
      dataDriven.financial_engineering = true;
    }
    if (fundamentals.payoutRatio != null) {
      const pr = fundamentals.payoutRatio;
      let prAdj = 0;
      if (pr >= 30 && pr <= 60) prAdj = 3;
      else if (pr > 100) prAdj = -8;
      else if (pr > 80) prAdj = -4;
      dims.financial_engineering = clamp(dims.financial_engineering + prAdj, 0, 100);
      dataDriven.financial_engineering = true;
    }
    if (fundamentals.epsCagr != null && sb.epsCagr) {
      const gDelta = (fundamentals.epsCagr - sb.epsCagr) / Math.max(1, Math.abs(sb.epsCagr));
      dims.strategic_transformation = clamp(dims.strategic_transformation + Math.round(gDelta * 8), 0, 100);
      dims.financial_metrics = clamp(dims.financial_metrics + Math.round(gDelta * 4), 0, 100);
      dataDriven.strategic_transformation = true;
    }
    if (fundamentals.epsCagr == null && fundamentals.quarterlyEarningsGrowth != null) {
      const anchor = sb.epsCagr || 8;
      const qDelta = (fundamentals.quarterlyEarningsGrowth - anchor) / Math.max(2, Math.abs(anchor));
      dims.strategic_transformation = clamp(dims.strategic_transformation + Math.round(qDelta * 5), 0, 100);
      dataDriven.strategic_transformation = true;
    }
    if (fundamentals.quarterlyRevenueGrowth != null) {
      const rgDelta = (fundamentals.quarterlyRevenueGrowth - 5) / 10;
      dims.strategic_transformation = clamp(dims.strategic_transformation + Math.round(rgDelta * 3), 0, 100);
      dataDriven.strategic_transformation = true;
    }
    if (!dataDriven.strategic_transformation && fundamentals.roe != null && fundamentals.debtEquity != null) {
      const roeAnchor = secId === 'TECH' ? 18 : secId === 'FIN' ? 11 : secId === 'UTIL' ? 9 : 13;
      const roeDelta = (fundamentals.roe - roeAnchor) / Math.max(5, roeAnchor);
      dims.strategic_transformation = clamp(dims.strategic_transformation + Math.round(roeDelta * 6), 0, 100);
      dataDriven.strategic_transformation = true;
    }
    if (fundamentals.beta != null) {
      const betaPenalty = Math.round((fundamentals.beta - 1.0) * -6);
      dims.market_dynamics = clamp(dims.market_dynamics + betaPenalty, 0, 100);
      dataDriven.market_dynamics = true;
    }
    if (fundamentals.priceInRange != null) {
      const pos = fundamentals.priceInRange;
      let rangeAdj;
      if (pos >= 0.3 && pos <= 0.7) rangeAdj = 4;
      else if (pos >= 0.7 && pos <= 0.9) rangeAdj = 1;
      else if (pos > 0.9) rangeAdj = -3;
      else if (pos >= 0.1 && pos <= 0.3) rangeAdj = -1;
      else rangeAdj = -5;
      dims.market_dynamics = clamp(dims.market_dynamics + rangeAdj, 0, 100);
      dataDriven.market_dynamics = true;
    }
    if (fundamentals.insiderOwnershipPct != null) {
      const ins = fundamentals.insiderOwnershipPct;
      let adj;
      if (ins >= 20) adj = 18;
      else if (ins >= 10) adj = 12;
      else if (ins >= 5) adj = 6;
      else if (ins >= 1) adj = 0;
      else adj = -6;
      dims.management_stake = clamp(dims.management_stake + adj, 0, 100);
      dataDriven.management_stake = true;
    }
    if (fundamentals.institutionalOwnershipPct != null) {
      const inst = fundamentals.institutionalOwnershipPct;
      let adj;
      if (inst >= 40 && inst <= 80) adj = 8;
      else if (inst > 80 && inst <= 95) adj = 3;
      else if (inst > 95) adj = -4;
      else if (inst >= 20 && inst < 40) adj = 4;
      else adj = -2;
      dims.ownership_structure = clamp(dims.ownership_structure + adj, 0, 100);
      dataDriven.ownership_structure = true;
    }
    if (fundamentals.rdIntensity != null) {
      const rd = fundamentals.rdIntensity;
      let adj;
      if (rd >= 15) adj = 15;
      else if (rd >= 8) adj = 10;
      else if (rd >= 4) adj = 5;
      else if (rd >= 1) adj = 0;
      else adj = -4;
      dims.tech_adoption = clamp(dims.tech_adoption + adj, 0, 100);
      dataDriven.tech_adoption = true;
    }
    if (fundamentals.macroRate != null || fundamentals.macroGdp != null || fundamentals.macroInflation != null) {
      let adj = 0; let signals = 0;
      if (fundamentals.macroRate != null) {
        if (fundamentals.macroRate < 3) adj += 4;
        else if (fundamentals.macroRate > 5) adj -= 4;
        signals++;
      }
      if (fundamentals.macroGdp != null) {
        if (fundamentals.macroGdp >= 2.5) adj += 6;
        else if (fundamentals.macroGdp < 0) adj -= 8;
        else if (fundamentals.macroGdp < 1) adj -= 3;
        signals++;
      }
      if (fundamentals.macroInflation != null) {
        if (fundamentals.macroInflation > 6) adj -= 5;
        else if (fundamentals.macroInflation < 1) adj -= 2;
        else if (fundamentals.macroInflation >= 1.5 && fundamentals.macroInflation <= 3) adj += 3;
        signals++;
      }
      if (signals > 0) {
        dims.macro_environment = clamp(dims.macro_environment + adj, 0, 100);
        dataDriven.macro_environment = true;
      }
    }
    if (fundamentals.glassdoorRating != null || fundamentals.glassdoorRecommend != null) {
      let adj = 0;
      if (fundamentals.glassdoorRating != null) {
        const delta = fundamentals.glassdoorRating - 3.5;
        adj += Math.round(delta * 10);
      }
      if (fundamentals.glassdoorRecommend != null) {
        const delta = (fundamentals.glassdoorRecommend - 65) / 10;
        adj += Math.round(delta * 2);
      }
      dims.culture_purpose = clamp(dims.culture_purpose + adj, 0, 100);
      dataDriven.culture_purpose = true;
    }
    if (fundamentals.esgRisk != null) {
      const risk = fundamentals.esgRisk;
      let adj;
      if (risk < 10) adj = 12;
      else if (risk < 20) adj = 6;
      else if (risk < 30) adj = 0;
      else if (risk < 40) adj = -6;
      else adj = -12;
      dims.progressive_practices = clamp(dims.progressive_practices + adj, 0, 100);
      dataDriven.progressive_practices = true;
    }
  }
  return { dims, dataDriven };
}

function computeLayerScores(dims) {
  const layerScores = {};
  for (const layer of LAYERS) {
    let sum = 0, count = 0;
    for (const dimId of layer.dimensions) {
      if (dimId.startsWith('_')) continue;
      if (dims[dimId] != null) { sum += dims[dimId]; count++; }
    }
    layerScores[layer.id] = count ? Math.round(sum / count) : 50;
  }
  return layerScores;
}

function computeComposite(layerScores) {
  let total = 0, weightSum = 0;
  for (const layer of LAYERS) {
    if (layerScores[layer.id] != null) {
      total += layerScores[layer.id] * layer.weight;
      weightSum += layer.weight;
    }
  }
  return weightSum > 0 ? Math.round(total / weightSum) : 50;
}

// CLI: read JSON test cases from stdin, score them, write results to stdout.
// Used by tests/test_parity.py. Each line of input is one test case:
//   {"id": "...", "stock": {...}, "fundamentals": {...}}
const input = require('fs').readFileSync(0, 'utf8');
const cases = JSON.parse(input);
const results = cases.map(c => {
  const { dims, dataDriven } = computeDimensions(c.stock, c.fundamentals);
  const layerScores = computeLayerScores(dims);
  const composite = computeComposite(layerScores);
  return { id: c.id, dims, dataDriven, layerScores, composite };
});
process.stdout.write(JSON.stringify(results));
