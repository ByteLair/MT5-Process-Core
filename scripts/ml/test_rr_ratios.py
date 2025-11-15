#!/usr/bin/env python3
"""
Teste simples: RR Ratios diferentes
Objetivo: encontrar melhor RR para atingir 52%+ win rate ou ROI positivo

Base: backtest_h1_conservative.py com diferentes TP values
"""

import subprocess
import sys

# Configurações a testar
TEST_CONFIGS = [
    {'name': 'RR 1:1 (baseline)', 'tp': 20, 'threshold': 0.55},
    {'name': 'RR 1:1.25', 'tp': 25, 'threshold': 0.55},
    {'name': 'RR 1:1.5', 'tp': 30, 'threshold': 0.55},
    {'name': 'RR 1:2', 'tp': 40, 'threshold': 0.55},
    {'name': 'Threshold 0.60 + RR 1:1', 'tp': 20, 'threshold': 0.60},
    {'name': 'Threshold 0.60 + RR 1:1.5', 'tp': 30, 'threshold': 0.60},
    {'name': 'Threshold 0.65 + RR 1:1.5', 'tp': 30, 'threshold': 0.65},
]

print("\n" + "="*80)
print("🔍 TESTE DE RR RATIOS E THRESHOLDS - H1 CONSERVADOR")
print("="*80)
print("\nObjetivo: Atingir 52%+ win rate ou ROI positivo")
print(f"Testando {len(TEST_CONFIGS)} configurações...\n")

results = []

for i, config in enumerate(TEST_CONFIGS, 1):
    print(f"\n[{i}/{len(TEST_CONFIGS)}] Testando: {config['name']}")
    print(f"  TP: {config['tp']} pips | Threshold: {config['threshold']}")
    print("  " + "-"*70)
    
    # Modificar o arquivo backtest
    with open('/tmp/backtest_h1_conservative.py', 'r') as f:
        content = f.read()
    
    # Substituir os valores
    content = content.replace('TAKE_PROFIT_PIPS = 20', f'TAKE_PROFIT_PIPS = {config["tp"]}')
    content = content.replace('THRESHOLD = 0.55', f'THRESHOLD = {config["threshold"]}')
    
    # Salvar temporariamente
    with open('/tmp/backtest_temp.py', 'w') as f:
        f.write(content)
    
    # Executar
    try:
        result = subprocess.run(
            ['python', '/tmp/backtest_temp.py'],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        # Extrair métricas do output
        output = result.stdout + result.stderr
        
        # Parse simples (procurar linhas chave)
        lines = output.split('\n')
        metrics = {
            'config': config['name'],
            'tp': config['tp'],
            'threshold': config['threshold']
        }
        
        for line in lines:
            if 'ROI:' in line and '%' in line:
                try:
                    metrics['roi'] = float(line.split(':')[-1].replace('%', '').strip())
                except:
                    pass
            if 'Win Rate:' in line and '%' in line:
                try:
                    metrics['win_rate'] = float(line.split(':')[-1].replace('%', '').strip())
                except:
                    pass
            if 'Total trades:' in line:
                try:
                    metrics['trades'] = int(line.split(':')[-1].strip())
                except:
                    pass
        
        results.append(metrics)
        
        # Imprimir resultado
        if 'roi' in metrics and 'win_rate' in metrics:
            print(f"  ✅ ROI: {metrics['roi']:.2f}% | Win Rate: {metrics['win_rate']:.1f}% | Trades: {metrics.get('trades', '?')}")
            
            # Destacar se atingiu metas
            if metrics['win_rate'] >= 52:
                print(f"  🎉 META DE WIN RATE ATINGIDA!")
            if metrics['roi'] > 0:
                print(f"  💰 ROI POSITIVO!")
        else:
            print(f"  ⚠️  Erro ao parsear resultados")
            
    except subprocess.TimeoutExpired:
        print(f"  ❌ Timeout (>60s)")
        results.append({'config': config['name'], 'error': 'timeout'})
    except Exception as e:
        print(f"  ❌ Erro: {e}")
        results.append({'config': config['name'], 'error': str(e)})

# Resumo final
print("\n" + "="*80)
print("📊 RESUMO DOS RESULTADOS")
print("="*80)

valid_results = [r for r in results if 'roi' in r and 'win_rate' in r]

if valid_results:
    # Ordenar por ROI
    valid_results.sort(key=lambda x: x['roi'], reverse=True)
    
    print("\n🏆 TOP CONFIGURAÇÕES POR ROI:\n")
    for i, r in enumerate(valid_results[:5], 1):
        icon = "🎉" if r['roi'] > 0 else "⚠️"
        wr_icon = "✅" if r['win_rate'] >= 52 else ""
        print(f"{i}. {r['config']}")
        print(f"   ROI: {r['roi']:+.2f}% {icon} | Win Rate: {r['win_rate']:.1f}% {wr_icon} | Trades: {r.get('trades', '?')}")
    
    # Melhor win rate
    best_wr = max(valid_results, key=lambda x: x['win_rate'])
    print(f"\n🎯 MELHOR WIN RATE: {best_wr['config']}")
    print(f"   {best_wr['win_rate']:.1f}% (ROI: {best_wr['roi']:+.2f}%)")
    
    # Melhor ROI
    best_roi = valid_results[0]
    print(f"\n💰 MELHOR ROI: {best_roi['config']}")
    print(f"   {best_roi['roi']:+.2f}% (Win Rate: {best_roi['win_rate']:.1f}%)")
    
    # Recomendação
    print("\n" + "="*80)
    print("🎯 RECOMENDAÇÃO FINAL:")
    print("="*80)
    
    if best_roi['roi'] > 0:
        print(f"\n✅ SISTEMA VIÁVEL com: {best_roi['config']}")
        print(f"   Usar TP={best_roi['tp']} pips, Threshold={best_roi['threshold']}")
        print(f"   Expectativa: {best_roi['roi']:+.2f}% ROI, {best_roi['win_rate']:.1f}% Win Rate")
    elif best_wr['win_rate'] >= 52:
        print(f"\n⚠️  Win rate de 52% atingido, mas ROI ainda negativo")
        print(f"   Melhor config: {best_wr['config']}")
        print(f"   Considerar aumentar mais o RR ratio")
    else:
        print(f"\n❌ Metas não atingidas ainda")
        print(f"   Melhor resultado: {best_roi['config']}")
        print(f"   ROI: {best_roi['roi']:+.2f}%, Win Rate: {best_roi['win_rate']:.1f}%")
        print(f"\n   Próximos passos:")
        print(f"   1. Adicionar filtros de qualidade (sessão, volatilidade)")
        print(f"   2. Treinar novo modelo com mais features")
        print(f"   3. Considerar H4 ou D1 timeframe")
else:
    print("\n❌ Nenhum resultado válido obtido")

print("\n✅ Teste concluído!\n")
