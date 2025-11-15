#!/usr/bin/env python3
"""
Batch Test: Múltiplas configurações RR + Threshold
Testa sistematicamente para encontrar melhor setup
"""
import subprocess
import sys
import re

# Configurações para testar
TESTS = [
    # Baseline
    {'name': 'Baseline RR 1:1', 'tp': 20, 'sl': 20, 'threshold': 0.55},
    
    # RR variations com threshold 0.55
    {'name': 'RR 1:1.25 (Th 0.55)', 'tp': 25, 'sl': 20, 'threshold': 0.55},
    {'name': 'RR 1:1.5 (Th 0.55)', 'tp': 30, 'sl': 20, 'threshold': 0.55},
    {'name': 'RR 1:2 (Th 0.55)', 'tp': 40, 'sl': 20, 'threshold': 0.55},
    
    # Threshold variations com RR 1:1
    {'name': 'Th 0.60 (RR 1:1)', 'tp': 20, 'sl': 20, 'threshold': 0.60},
    {'name': 'Th 0.65 (RR 1:1)', 'tp': 20, 'sl': 20, 'threshold': 0.65},
    {'name': 'Th 0.70 (RR 1:1)', 'tp': 20, 'sl': 20, 'threshold': 0.70},
    
    # Combinações otimizadas
    {'name': 'RR 1:1.5 + Th 0.60', 'tp': 30, 'sl': 20, 'threshold': 0.60},
    {'name': 'RR 1:1.5 + Th 0.65', 'tp': 30, 'sl': 20, 'threshold': 0.65},
    {'name': 'RR 1:2 + Th 0.65', 'tp': 40, 'sl': 20, 'threshold': 0.65},
]

def extract_metrics(output):
    """Extrai métricas do output do backtest"""
    metrics = {}
    
    # ROI
    match = re.search(r'ROI:\s+([-+]?\d+\.?\d*)%', output)
    if match:
        metrics['roi'] = float(match.group(1))
    
    # Win Rate
    match = re.search(r'Trades Vencedores:\s+(\d+)\s+\(([\d.]+)%\)', output)
    if match:
        metrics['wins'] = int(match.group(1))
        metrics['win_rate'] = float(match.group(2))
    
    # Total Trades
    match = re.search(r'Total de Trades:\s+(\d+)', output)
    if match:
        metrics['total_trades'] = int(match.group(1))
    
    # Max DD
    match = re.search(r'Max Drawdown:\s+([-+]?\d+\.?\d*)%', output)
    if match:
        metrics['max_dd'] = float(match.group(1))
    
    # Profit Factor
    match = re.search(r'Profit Factor:\s+([\d.]+)', output)
    if match:
        metrics['profit_factor'] = float(match.group(1))
    
    # Sharpe
    match = re.search(r'Sharpe Ratio:\s+([-+]?\d+\.?\d*)', output)
    if match:
        metrics['sharpe'] = float(match.group(1))
    
    # Capital Final
    match = re.search(r'Capital Final:\s+\$([0-9,]+\.?\d*)', output)
    if match:
        capital_str = match.group(1).replace(',', '')
        metrics['final_capital'] = float(capital_str)
    
    return metrics

def run_test(config):
    """Executa um teste com configuração específica"""
    print(f"\n{'='*80}")
    print(f"🧪 TESTE: {config['name']}")
    print(f"{'='*80}")
    print(f"  TP: {config['tp']} pips | SL: {config['sl']} pips | Threshold: {config['threshold']}")
    print(f"  RR Ratio: 1:{config['tp']/config['sl']:.2f}")
    
    # Ler template
    with open('/tmp/backtest_h1_rr_1_5.py', 'r') as f:
        code = f.read()
    
    # Modificar parâmetros
    code = re.sub(r'TAKE_PROFIT_PIPS = \d+', f'TAKE_PROFIT_PIPS = {config["tp"]}', code)
    code = re.sub(r'STOP_LOSS_PIPS = \d+', f'STOP_LOSS_PIPS = {config["sl"]}', code)
    code = re.sub(r'THRESHOLD = [\d.]+', f'THRESHOLD = {config["threshold"]}', code)
    
    # Salvar temporário
    with open('/tmp/backtest_temp.py', 'w') as f:
        f.write(code)
    
    # Executar
    try:
        result = subprocess.run(
            ['python', '/tmp/backtest_temp.py'],
            capture_output=True,
            text=True,
            timeout=120
        )
        
        output = result.stdout + result.stderr
        metrics = extract_metrics(output)
        
        if metrics:
            print(f"\n  📊 RESULTADOS:")
            print(f"     ROI:          {metrics.get('roi', 'N/A'):>8}%")
            print(f"     Win Rate:     {metrics.get('win_rate', 'N/A'):>8}%")
            print(f"     Trades:       {metrics.get('total_trades', 'N/A'):>8}")
            print(f"     Profit Factor:{metrics.get('profit_factor', 'N/A'):>8}")
            print(f"     Max DD:       {metrics.get('max_dd', 'N/A'):>8}%")
            print(f"     Sharpe:       {metrics.get('sharpe', 'N/A'):>8}")
            
            # Destacar se atingiu metas
            roi = metrics.get('roi', -999)
            win_rate = metrics.get('win_rate', 0)
            
            if roi > 0:
                print(f"\n  ✅ ROI POSITIVO!")
            if win_rate >= 52:
                print(f"  🎯 WIN RATE ≥ 52%!")
            if roi > 0 and win_rate >= 52:
                print(f"\n  🎉🎉🎉 META COMPLETA ATINGIDA! 🎉🎉🎉")
                
            return {**config, **metrics, 'status': 'success'}
        else:
            print(f"  ⚠️  Não foi possível extrair métricas")
            return {**config, 'status': 'parse_error'}
            
    except subprocess.TimeoutExpired:
        print(f"  ❌ Timeout (>120s)")
        return {**config, 'status': 'timeout'}
    except Exception as e:
        print(f"  ❌ Erro: {e}")
        return {**config, 'status': 'error', 'error': str(e)}

def main():
    print("\n" + "="*80)
    print("🔬 BATCH TEST: OTIMIZAÇÃO H1")
    print("="*80)
    print(f"\nTestando {len(TESTS)} configurações diferentes...")
    print("Objetivo: Encontrar setup com ROI > 0% e/ou Win Rate ≥ 52%")
    
    results = []
    
    for i, test in enumerate(TESTS, 1):
        print(f"\n\n[{i}/{len(TESTS)}]", end=' ')
        result = run_test(test)
        results.append(result)
    
    # Análise dos resultados
    print("\n\n" + "="*80)
    print("📊 RESUMO GERAL DOS TESTES")
    print("="*80)
    
    successful = [r for r in results if r.get('status') == 'success' and 'roi' in r]
    
    if not successful:
        print("\n❌ Nenhum teste completou com sucesso")
        return
    
    # Ordenar por ROI
    successful.sort(key=lambda x: x.get('roi', -999), reverse=True)
    
    print(f"\n🏆 TOP 5 POR ROI:")
    print(f"{'─'*80}")
    for i, r in enumerate(successful[:5], 1):
        icon_roi = "✅" if r['roi'] > 0 else "❌"
        icon_wr = "🎯" if r.get('win_rate', 0) >= 52 else ""
        print(f"\n{i}. {r['name']}")
        print(f"   ROI: {r['roi']:+.2f}% {icon_roi} | Win Rate: {r.get('win_rate', 0):.1f}% {icon_wr}")
        print(f"   Trades: {r.get('total_trades', 0)} | PF: {r.get('profit_factor', 0):.2f} | DD: {r.get('max_dd', 0):.2f}%")
    
    # Melhor Win Rate
    best_wr = max(successful, key=lambda x: x.get('win_rate', 0))
    print(f"\n\n🎯 MELHOR WIN RATE:")
    print(f"{'─'*80}")
    print(f"   {best_wr['name']}")
    print(f"   Win Rate: {best_wr.get('win_rate', 0):.1f}% | ROI: {best_wr.get('roi', 0):+.2f}%")
    
    # Melhor ROI
    best_roi = successful[0]
    print(f"\n\n💰 MELHOR ROI:")
    print(f"{'─'*80}")
    print(f"   {best_roi['name']}")
    print(f"   ROI: {best_roi.get('roi', 0):+.2f}% | Win Rate: {best_roi.get('win_rate', 0):.1f}%")
    
    # Configs viáveis
    viable = [r for r in successful if r.get('roi', -999) > 0]
    print(f"\n\n✅ CONFIGURAÇÕES VIÁVEIS (ROI > 0%):")
    print(f"{'─'*80}")
    if viable:
        for r in viable:
            print(f"   • {r['name']}: ROI {r['roi']:+.2f}%, WR {r.get('win_rate', 0):.1f}%")
    else:
        print(f"   ⚠️  Nenhuma configuração atingiu ROI positivo")
    
    # Meta 52%
    meta_52 = [r for r in successful if r.get('win_rate', 0) >= 52]
    print(f"\n\n🎯 CONFIGURAÇÕES COM WIN RATE ≥ 52%:")
    print(f"{'─'*80}")
    if meta_52:
        for r in meta_52:
            print(f"   • {r['name']}: WR {r.get('win_rate', 0):.1f}%, ROI {r.get('roi', 0):+.2f}%")
    else:
        print(f"   ⚠️  Nenhuma configuração atingiu 52% win rate")
    
    # Recomendação final
    print(f"\n\n" + "="*80)
    print("🎯 RECOMENDAÇÃO FINAL")
    print("="*80)
    
    if viable and meta_52:
        # Ideal: viável E com 52%
        ideal = [r for r in successful if r.get('roi', -999) > 0 and r.get('win_rate', 0) >= 52]
        if ideal:
            best = ideal[0]
            print(f"\n✅✅✅ CONFIGURAÇÃO IDEAL ENCONTRADA! ✅✅✅")
            print(f"\n   {best['name']}")
            print(f"   • TP: {best['tp']} pips | SL: {best['sl']} pips | Threshold: {best['threshold']}")
            print(f"   • ROI: {best['roi']:+.2f}% ✅")
            print(f"   • Win Rate: {best.get('win_rate', 0):.1f}% 🎯")
            print(f"   • Profit Factor: {best.get('profit_factor', 0):.2f}")
            print(f"   • Max Drawdown: {best.get('max_dd', 0):.2f}%")
            print(f"\n   🚀 PRONTO PARA PAPER TRADING!")
        else:
            print(f"\n✅ Sistema viável, mas ainda sem 52% win rate")
            print(f"   Melhor config: {best_roi['name']}")
            print(f"   ROI: {best_roi['roi']:+.2f}% | WR: {best_roi.get('win_rate', 0):.1f}%")
    elif viable:
        print(f"\n✅ SISTEMA VIÁVEL encontrado!")
        print(f"   Config: {best_roi['name']}")
        print(f"   ROI: {best_roi['roi']:+.2f}% ✅")
        print(f"   Win Rate: {best_roi.get('win_rate', 0):.1f}%")
        print(f"\n   Próximo: Adicionar filtros para melhorar win rate")
    elif meta_52:
        print(f"\n🎯 Meta de 52% atingida, mas ROI ainda negativo")
        print(f"   Config: {best_wr['name']}")
        print(f"   Win Rate: {best_wr.get('win_rate', 0):.1f}% 🎯")
        print(f"   ROI: {best_wr.get('roi', 0):+.2f}%")
        print(f"\n   Próximo: Aumentar RR ratio para viabilizar")
    else:
        print(f"\n⚠️  Metas não atingidas")
        print(f"   Melhor resultado: {best_roi['name']}")
        print(f"   ROI: {best_roi['roi']:+.2f}% | WR: {best_roi.get('win_rate', 0):.1f}%")
        print(f"\n   Próximos passos:")
        print(f"   1. Implementar filtros de qualidade (sessão, ATR, ADX)")
        print(f"   2. Re-treinar modelo com features multi-timeframe")
        print(f"   3. Considerar H4 ou D1 timeframe")
    
    print(f"\n\n✅ Batch test concluído!")
    print(f"   Total testado: {len(TESTS)} configs")
    print(f"   Sucesso: {len(successful)}")
    print(f"   Viáveis (ROI>0): {len(viable)}")
    print(f"   Meta 52%: {len(meta_52)}\n")

if __name__ == '__main__':
    main()
