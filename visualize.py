from datetime import datetime
import plotly.graph_objects as go
import streamlit as st

def visualize_schedule_interactive(user_slots, scheduled_program, yontem):
    days_order = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
    
    # Tür renkleri
    program_colors = {
        "haber": "#FF0000",    # Kırmızı
        "dizi": "#00FF00",     # Yeşil
        "eglence": "#660099",  # Mavi
        "spor": "#FFA500",     # Turuncu
        "yasam": "#FFFF00",    # Sari
        "film": "#FF1493",     # Pembe
        "Çizgi Dizi": "#00FFFF" # Turkuaz        
    }
    
    fig = go.Figure()
    
    # Tüm haftayı gri arka plan olarak çiz
    for day in days_order:
        fig.add_trace(go.Bar(
            x=[24],
            y=[day],
            orientation='h',
            marker=dict(color='rgba(200,200,200,0.3)', line=dict(width=0)),
            hoverinfo='skip',
            showlegend=False
        ))
    
    # Kullanıcının müsait olduğu slotları çiz
    for slot in user_slots:
        start = datetime.strptime(slot["start_time"], "%H:%M")
        end = datetime.strptime(slot["end_time"], "%H:%M")
        duration = (end - start).seconds / 3600
        
        fig.add_trace(go.Bar(
            x=[duration],
            y=[slot["day"]],
            orientation='h',
            marker=dict(color='rgba(211,211,211,0.7)'),
            base=start.hour + start.minute / 60,
            hoverinfo='skip',
            showlegend=False
        ))
    
    # Legend için eklenen program türlerini takip edelim
    added_types = set()
    
    # Programları çiz
    for program_info, _ in scheduled_program:  # slot bilgisi kullanılmıyor
        start_str = program_info["Başlangıç Saati"]
        end_str = program_info["Bitiş Saati"]
        
        start = datetime.strptime(start_str, "%H:%M")
        end = datetime.strptime(end_str, "%H:%M")
        duration = (end - start).seconds / 3600
        
        program_type = program_info["Tür"]
        color = program_colors.get(program_type, "#808080")  # Varsayılan gri
        
        hover_text = (f"<b>{program_info['Ad']}</b><br>"
                      f"Tür: {program_type}<br>"
                      f"Kanal: {program_info['Kanal']}<br>"
                      f"Süre: {duration:.2f} saat<br>"
                      f"Başlangıç: {start_str}<br>"
                      f"Bitiş: {end_str}")
        
        # Her türden ilk kez eklenirken legend'da göster, sonrakiler gizlensin
        show_legend = False
        if program_type not in added_types:
            show_legend = True
            added_types.add(program_type)
        
        fig.add_trace(go.Bar(
            x=[duration],
            y=[program_info["Gün"]],
            orientation='h',
            marker=dict(color=color,line=dict(width=1)),
            opacity=0.9,
            base=start.hour + start.minute / 60,
            name=program_type,
            hovertext=hover_text,
            hoverinfo="text",
            textposition='none',
            showlegend=show_legend
        ))
    
    # Eksen ve layout ayarları
    fig.update_layout(
        barmode='stack',
        xaxis=dict(
            title="Saat",
            range=[0,24],
            dtick=1,
            tickformat="%H:%M",
            tickvals=list(range(25))
        ),
        yaxis=dict(
            title="Gün",
            categoryorder='array',
            categoryarray=days_order
        ),
        title="TV Program Planlama"+yontem,
        hoverlabel=dict(
            bgcolor="white",
            font_size=12,
            font_family="Arial"
        ),
        legend_title="Program Türleri"
    )
    
    # X eksenini saat formatına çevirme
    fig.update_xaxes(
        ticktext=[f"{h:02d}:00" for h in range(25)],
        tickvals=list(range(25))
    )
    
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

