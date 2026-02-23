#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
RL Training Integration - Integra scheduler com sistema de trading
Dispara treinamento automático após fechamento do mercado
"""
import time
import logging
import subprocess
import sys
from datetime import datetime, time as dt_time
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('logs/rl_integration.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class RLTrainingIntegration:
    """Integra RL training com sistema de trading"""
    
    def __init__(self):
        Path('logs').mkdir(exist_ok=True)
        logger.info("=" * 60)
        logger.info("🔗 RL TRAINING INTEGRATION - INICIALIZADO")
        logger.info("=" * 60)
        
        self.market_close_time = dt_time(17, 0)  # 17:00 (5 PM)
        self.training_delay = 120  # 2 minutos após fechamento (5:02 PM)
    
    def is_market_closed(self):
        """Verifica se mercado está fechado"""
        now = datetime.now()
        current_time = now.time()
        
        # Mercado fecha às 17:00 (5 PM)
        # Considerar fechado após 17:00
        market_closed = current_time >= self.market_close_time
        
        # Não treinar fora do horário comercial (não madrugada)
        sensible_time = dt_time(4, 0) < current_time < dt_time(23, 59)
        
        return market_closed and sensible_time
    
    def should_train_today(self):
        """Verifica se é um dia útil (seg-sex)"""
        today = datetime.now().weekday()
        return today < 5  # 0-4 = seg-sex
    
    def run_training(self):
        """Executa treinamento RL"""
        logger.info("\n🚀 DISPARANDO TREINAMENTO RL...")
        
        try:
            # Importar aqui para evitar circular imports
            from scripts.rl_training_scheduler import RLTrainingScheduler
            
            scheduler = RLTrainingScheduler()
            success = scheduler.run_once()
            
            if success:
                logger.info("✅ TREINAMENTO COMPLETADO COM SUCESSO")
                return True
            else:
                logger.error("❌ TREINAMENTO FALHOU")
                return False
        
        except Exception as e:
            logger.error(f"❌ Erro ao executar treinamento: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def watch_and_train(self, check_interval=60):
        """
        Monitora fechamento do mercado e dispara treinamento
        
        Args:
            check_interval: Intervalo de check em segundos (default: 60)
        """
        logger.info(f"👁️ Monitorando mercado (check a cada {check_interval}s)...")
        logger.info(f"   Market close: {self.market_close_time}")
        logger.info(f"   Training delay: {self.training_delay}s\n")
        
        trained_today = False
        consecutive_errors = 0
        max_errors = 3
        
        try:
            while True:
                now = datetime.now()
                current_time = now.time()
                
                # Verificar se já treinamos hoje
                if trained_today and current_time < self.market_close_time:
                    trained_today = False  # Reset para próximo dia
                
                # Se mercado fechou e ainda não treinamos
                if self.is_market_closed() and not trained_today:
                    if self.should_train_today():
                        logger.info(f"\n{'='*60}")
                        logger.info(f"📊 MERCADO FECHADO - {datetime.now()}")
                        logger.info(f"{'='*60}")
                        
                        # Aguardar delay
                        logger.info(f"⏳ Aguardando {self.training_delay}s antes do treinamento...")
                        time.sleep(self.training_delay)
                        
                        # Treinar
                        if self.run_training():
                            trained_today = True
                            consecutive_errors = 0
                        else:
                            consecutive_errors += 1
                            if consecutive_errors >= max_errors:
                                logger.error(f"🚨 {max_errors} erros consecutivos - pausando")
                                time.sleep(3600)  # Pausar 1 hora
                    else:
                        logger.info(f"📅 Fim de semana ({datetime.now().strftime('%A')}) - sem treinamento")
                        trained_today = True
                
                # Sleep e check novamente
                time.sleep(check_interval)
        
        except KeyboardInterrupt:
            logger.info("\n⛔ Monitoramento encerrado pelo usuário")
        except Exception as e:
            logger.error(f"\n❌ Erro em watch_and_train: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def run_scheduler_and_watch(self, scheduler_time='22:00'):
        """
        Executa scheduler completo + monitoramento de mercado
        Combina os dois em um único processo
        """
        logger.info("\n" + "=" * 60)
        logger.info("🔄 MODO HÍBRIDO: Scheduler + Market Watch")
        logger.info("=" * 60)
        logger.info(f"   Scheduler time: {scheduler_time} (daily)")
        logger.info(f"   Market watch: autom após 17:00\n")
        
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger
        
        scheduler = BackgroundScheduler()
        
        # Agendar scheduler normal (backup)
        hour, minute = map(int, scheduler_time.split(':'))
        trigger = CronTrigger(hour=hour, minute=minute, day_of_week='mon-fri')
        scheduler.add_job(
            self.run_training,
            trigger=trigger,
            id='rl_scheduled',
            name='RL Scheduled Training'
        )
        
        scheduler.start()
        logger.info(f"✅ Scheduler agendado para {scheduler_time}")
        
        # Iniciar monitoramento de mercado
        self.watch_and_train(check_interval=300)  # Check a cada 5 min

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='RL Training Integration')
    parser.add_argument(
        '--mode',
        choices=['watch', 'scheduler', 'hybrid'],
        default='watch',
        help='Modo de operação'
    )
    parser.add_argument(
        '--scheduler-time',
        default='22:00',
        help='Hora do scheduler (HH:MM)'
    )
    parser.add_argument(
        '--check-interval',
        type=int,
        default=60,
        help='Intervalo de check em segundos'
    )
    
    args = parser.parse_args()
    
    integration = RLTrainingIntegration()
    
    if args.mode == 'watch':
        logger.info("📍 Modo: Market Watch")
        integration.watch_and_train(check_interval=args.check_interval)
    
    elif args.mode == 'scheduler':
        logger.info("📍 Modo: Scheduler puro")
        from scripts.rl_training_scheduler import RLTrainingScheduler
        scheduler = RLTrainingScheduler()
        scheduler.schedule_training(time_of_day=args.scheduler_time)
        scheduler.schedule_weekly_deep_training()
        scheduler.start()
        
        try:
            import time
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("⛔ Scheduler parado")
            scheduler.stop()
    
    elif args.mode == 'hybrid':
        logger.info("📍 Modo: Híbrido (Scheduler + Market Watch)")
        integration.run_scheduler_and_watch(scheduler_time=args.scheduler_time)

if __name__ == '__main__':
    main()
