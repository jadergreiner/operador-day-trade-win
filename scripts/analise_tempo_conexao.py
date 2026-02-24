import sqlite3
from datetime import datetime

db_path = r'C:\repo\operador-day-trade-win\data\db\trading.db'

def analyze_connection_time(db_path):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Obter timestamps formatados
        cursor.execute("SELECT timestamp FROM micro_trend_decisions ORDER BY timestamp ASC")
        rows = cursor.fetchall()

        if not rows:
            print("Nenhuma decisão encontrada no banco de dados.")
            return

        timestamps = [datetime.fromisoformat(row[0]) for row in rows]

        # Identificar sessões (supondo que gaps grandes indicam desconexão/final de dia)
        # 120 segundos é o ciclo normal. Se houver mais de 5 minutos, consideramos nova 'sessão' de atividade.
        GAP_THRESHOLD_SECONDS = 300

        sessions = []
        if timestamps:
            current_start = timestamps[0]
            last_ts = timestamps[0]

            for i in range(1, len(timestamps)):
                delta = (timestamps[i] - last_ts).total_seconds()
                if delta > GAP_THRESHOLD_SECONDS:
                    # Fim da sessão
                    sessions.append((current_start, last_ts))
                    current_start = timestamps[i]
                last_ts = timestamps[i]

            # Adicionar última sessão
            sessions.append((current_start, last_ts))

        total_duration = sum([(end - start).total_seconds() for start, end in sessions])
        total_hours = total_duration / 3600

        print(f"Número total de entradas (ciclos): {len(timestamps)}")
        print(f"Primeira conexão: {timestamps[0]}")
        print(f"Última conexão: {timestamps[-1]}")
        print(f"Total de sessões de atividade detectadas: {len(sessions)}")
        print(f"Tempo total conectado (líquido): {total_hours:.2f} horas")

        # Breakdown por dia
        from collections import defaultdict
        daily_time = defaultdict(float)
        for start, end in sessions:
            daily_time[start.date()] += (end - start).total_seconds()

        print("\nBreakdown por dia:")
        for day, seconds in sorted(daily_time.items()):
            print(f" - {day}: {seconds/3600:.2f} horas")

    except Exception as e:
        print(f"Erro ao analisar DB: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    analyze_connection_time(db_path)
