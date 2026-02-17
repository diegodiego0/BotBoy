
from telebot import types
import json
from typing import Dict, List, Optional, Any

class IPTVFrontend:
    def __init__(self, bot):
        self.bot = bot
        self.items_per_page = 8
        self.max_button_text = 35
    
    def create_error_message(self, error_msg: str, back_callback: str = "menu_principal") -> types.InlineKeyboardMarkup:
        keyboard = types.InlineKeyboardMarkup()
        btn_back = types.InlineKeyboardButton("🔙 Voltar", callback_data=back_callback)
        keyboard.add(btn_back)
        return keyboard
    
    def truncate_text(self, text: str, max_length: int = None) -> str:
        if max_length is None:
            max_length = self.max_button_text
        return text[:max_length-3] + "..." if len(text) > max_length else text
    
    def create_pagination_buttons(self, page: int, total_items: int, callback_prefix: str, *args) -> List[types.InlineKeyboardButton]:
        buttons = []
        total_pages = (total_items + self.items_per_page - 1) // self.items_per_page
        
        if page > 0:
            callback_data = f"{callback_prefix}_{'_'.join(map(str, args))}_{page-1}"
            buttons.append(types.InlineKeyboardButton("⬅️ Anterior", callback_data=callback_data))
        
        # Page indicator
        buttons.append(types.InlineKeyboardButton(f"📄 {page + 1}/{total_pages}", callback_data="page_info"))
        
        if (page + 1) * self.items_per_page < total_items:
            callback_data = f"{callback_prefix}_{'_'.join(map(str, args))}_{page+1}"
            buttons.append(types.InlineKeyboardButton("➡️ Próximo", callback_data=callback_data))
        
        return buttons
    
    def show_main_menu(self, chat_id: int, message_id: int = None):
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        
        btn_canais = types.InlineKeyboardButton("📺 Canais de TV", callback_data="menu_canais")
        btn_filmes = types.InlineKeyboardButton("🎬 Filmes", callback_data="menu_filmes") 
        btn_series = types.InlineKeyboardButton("📺 Séries", callback_data="menu_series")
        btn_selections = types.InlineKeyboardButton("⭐ Minhas Seleções", callback_data="menu_selections")
        btn_server_info = types.InlineKeyboardButton("ℹ️ Info do Servidor", callback_data="server_info")
        btn_nova_playlist = types.InlineKeyboardButton("🔄 Nova Playlist", callback_data="nova_playlist")
        
        keyboard.add(btn_canais, btn_filmes, btn_series)
        keyboard.add(btn_selections, btn_server_info)
        keyboard.add(btn_nova_playlist)
        
        text = """
🎯 **MENU PRINCIPAL**

🚀 **Bot IPTV Profissional v2.0**

**Funcionalidades disponíveis:**
📺 **Canais** - TV ao vivo com categorias
🎬 **Filmes** - Catálogo completo com info
📺 **Séries** - Temporadas e episódios
⭐ **Seleções** - Seus favoritos salvos
ℹ️ **Info** - Dados do servidor/usuário
🔄 **Playlist** - Configurar nova URL

**💡 Recursos únicos:**
• Geração de arquivos M3U personalizados
• Sistema anti-spam e cache inteligente
• Interface profissional com paginação
• Categorias personalizáveis
        """
        
        try:
            if message_id:
                self.bot.edit_message_text(text, chat_id, message_id, reply_markup=keyboard, parse_mode='Markdown')
            else:
                self.bot.send_message(chat_id, text, reply_markup=keyboard, parse_mode='Markdown')
        except Exception as e:
            print(f"Error showing main menu: {e}")
    
    def show_loading_message(self, chat_id: int, text: str = "⏳ Carregando...") -> int:
        try:
            msg = self.bot.send_message(chat_id, text)
            return msg.message_id
        except:
            return None
    
    def show_server_info(self, chat_id: int, message_id: int, server_info: Dict):
        keyboard = types.InlineKeyboardMarkup()
        btn_back = types.InlineKeyboardButton("🔙 Menu Principal", callback_data="menu_principal")
        keyboard.add(btn_back)
        
        if not server_info:
            text = "❌ **Erro ao obter informações do servidor**"
        else:
            exp_date = server_info.get('exp_date', 'N/A')
            if exp_date and exp_date != 'N/A' and exp_date.isdigit():
                from datetime import datetime
                exp_date = datetime.fromtimestamp(int(exp_date)).strftime('%d/%m/%Y %H:%M')
            
            text = f"""
ℹ️ **INFORMAÇÕES DO SERVIDOR**

**🖥️ Servidor:**
• URL: `{server_info.get('server', 'N/A')}`
• Status: {'🟢 Ativo' if server_info.get('status') == 'Active' else '🔴 Inativo'}

**👤 Usuário:**
• Login: `{server_info.get('username', 'N/A')}`
• Expira em: {exp_date}
• Conexões ativas: {server_info.get('active_cons', '0')}/{server_info.get('max_connections', '1')}

**📊 Conteúdo disponível:**
• 📺 Canais: {server_info.get('available_channels', '0')}
• 🎬 Filmes: {server_info.get('available_movies', '0')}
• 📺 Séries: {server_info.get('available_series', '0')}

**⚡ Status da conexão:** {'🟢 Estável' if server_info else '🔴 Instável'}
            """
        
        try:
            self.bot.edit_message_text(text, chat_id, message_id, reply_markup=keyboard, parse_mode='Markdown')
        except Exception as e:
            print(f"Error showing server info: {e}")
    
    def show_selections_menu(self, chat_id: int, message_id: int, selections: Dict):
        keyboard = types.InlineKeyboardMarkup(row_width=2)
        
        # Count items
        channels_count = len(selections.get('channels', []))
        movies_count = len(selections.get('movies', []))
        series_count = len(selections.get('series', []))
        total = channels_count + movies_count + series_count
        
        if total > 0:
            btn_view_channels = types.InlineKeyboardButton(f"📺 Canais ({channels_count})", callback_data="view_selected_channels")
            btn_view_movies = types.InlineKeyboardButton(f"🎬 Filmes ({movies_count})", callback_data="view_selected_movies")
            btn_view_series = types.InlineKeyboardButton(f"📺 Séries ({series_count})", callback_data="view_selected_series")
            
            keyboard.row(btn_view_channels, btn_view_movies)
            keyboard.add(btn_view_series)
            
            keyboard.add(types.InlineKeyboardButton("📄 Gerar M3U", callback_data="generate_m3u"))
            keyboard.add(types.InlineKeyboardButton("🗑️ Limpar Tudo", callback_data="clear_selections"))
        
        btn_back = types.InlineKeyboardButton("🔙 Menu Principal", callback_data="menu_principal")
        keyboard.add(btn_back)
        
        text = f"""
⭐ **SUAS SELEÇÕES**

**📊 Resumo:**
• 📺 Canais selecionados: **{channels_count}**
• 🎬 Filmes selecionados: **{movies_count}**
• 📺 Séries selecionadas: **{series_count}**
• **Total:** {total} itens

{'**🎉 Você pode gerar arquivos M3U personalizados!**' if total > 0 else '**📝 Nenhum item selecionado ainda.**'}

**💡 Dica:** Use os botões ⭐ ao navegar pelos conteúdos para adicionar às suas seleções.
        """
        
        try:
            self.bot.edit_message_text(text, chat_id, message_id, reply_markup=keyboard, parse_mode='Markdown')
        except Exception as e:
            print(f"Error showing selections menu: {e}")
    
    def show_rate_limit_error(self, chat_id: int):
        text = """
⚠️ **Muitas solicitações!**

Você está fazendo muitas solicitações muito rapidamente.
Aguarde alguns segundos antes de tentar novamente.

**⏰ Limite:** 5 solicitações por minuto
**🛡️ Proteção:** Anti-spam ativada
        """
        try:
            self.bot.send_message(chat_id, text, parse_mode='Markdown')
        except Exception as e:
            print(f"Error showing rate limit: {e}")

# Frontend instance will be created in main bot
frontend = None
