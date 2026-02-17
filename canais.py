
import requests
from telebot import types
import json
import time

class CanalManager:
    def __init__(self, bot, backend, frontend):
        self.bot = bot
        self.backend = backend
        self.frontend = frontend
        
    def get_categories(self, config):
        """Obtém categorias de canais"""
        params = {
            'username': config['username'],
            'password': config['password'],
            'action': 'get_live_categories'
        }
        
        return self.backend.make_api_request(config, params) or []
    
    def get_channels(self, config, category_id=None):
        """Obtém lista de canais"""
        params = {
            'username': config['username'],
            'password': config['password'],
            'action': 'get_live_streams'
        }
        
        if category_id:
            params['category_id'] = category_id
        
        channels = self.backend.make_api_request(config, params) or []
        
        # Adiciona URL de reprodução e preserva categoria original
        categories = self.get_categories(config)
        category_map = {str(cat.get('category_id')): cat.get('category_name', 'Canais') for cat in categories}
        
        for channel in channels:
            channel['play_url'] = f"{config['server']}/live/{config['username']}/{config['password']}/{channel['stream_id']}.{channel.get('container_extension', 'ts')}"
            # Preserva categoria original
            if not channel.get('category_name') and category_id:
                channel['category_name'] = category_map.get(str(category_id), 'Canais')
        
        return channels
    
    def show_categories(self, chat_id, message_id, config):
        """Mostra categorias de canais com opção de adicionar categoria completa"""
        try:
            categories = self.get_categories(config)
            
            if not categories:
                keyboard = self.frontend.create_error_message("❌ Nenhuma categoria de canais encontrada.")
                text = "❌ Não foi possível carregar as categorias de canais."
                try:
                    self.bot.edit_message_text(text, chat_id, message_id, reply_markup=keyboard)
                except Exception as e:
                    print(f"Error editing message: {e}")
                    self.bot.send_message(chat_id, text, reply_markup=keyboard)
                return
            
            keyboard = types.InlineKeyboardMarkup(row_width=1)
            
            # Adiciona botão para todos os canais
            btn_all = types.InlineKeyboardButton("📺 Todos os Canais", callback_data="canal_list_all_0")
            keyboard.add(btn_all)
            
            # Adiciona categorias (máximo 12) com botões para navegar e adicionar categoria completa
            for i, category in enumerate(categories[:12]):
                category_name = self.frontend.truncate_text(category['category_name'], 25)
                
                # Linha com botão de navegação e botão de adicionar categoria completa
                btn_nav = types.InlineKeyboardButton(
                    f"📁 {category_name}", 
                    callback_data=f"canal_list_{category['category_id']}_0"
                )
                btn_add_all = types.InlineKeyboardButton(
                    "📥➕", 
                    callback_data=f"add_full_category_channels_{category['category_id']}"
                )
                keyboard.row(btn_nav, btn_add_all)
            
            # Botão voltar
            btn_back = types.InlineKeyboardButton("🔙 Menu Principal", callback_data="menu_principal")
            keyboard.add(btn_back)
            
            text = f"""
📺 **CATEGORIAS DE CANAIS**

📊 **{len(categories)} categorias encontradas**
🎯 **Navegação otimizada**

**💡 Como usar:**
• 📁 **Nome da categoria**: Navegar pelos canais
• 📥➕ **Adicionar categoria**: Adiciona todos os canais da categoria ao M3U

**🏷️ Dica:** Ao adicionar categoria completa, você pode renomear!

Escolha uma categoria:
            """
            
            try:
                self.bot.edit_message_text(text, chat_id, message_id, reply_markup=keyboard, parse_mode='Markdown')
            except Exception as e:
                print(f"Error editing categories message: {e}")
                try:
                    self.bot.delete_message(chat_id, message_id)
                except:
                    pass
                self.bot.send_message(chat_id, text, reply_markup=keyboard, parse_mode='Markdown')
            
        except Exception as e:
            print(f"Error showing channel categories: {e}")
            keyboard = self.frontend.create_error_message("Erro ao carregar categorias")
            text = "❌ Erro ao carregar categorias. Tente novamente."
            try:
                self.bot.edit_message_text(text, chat_id, message_id, reply_markup=keyboard)
            except:
                self.bot.send_message(chat_id, text, reply_markup=keyboard)
    
    def show_channels(self, chat_id, message_id, config, category_id, page=0):
        """Mostra lista de canais com paginação"""
        try:
            if category_id == "all":
                channels = self.get_channels(config)
            else:
                channels = self.get_channels(config, category_id)
            
            if not channels:
                keyboard = self.frontend.create_error_message("❌ Nenhum canal encontrado.", "menu_canais")
                text = "❌ Nenhum canal encontrado nesta categoria."
                try:
                    self.bot.edit_message_text(text, chat_id, message_id, reply_markup=keyboard)
                except Exception as e:
                    print(f"Error editing no channels message: {e}")
                    self.bot.send_message(chat_id, text, reply_markup=keyboard)
                return
            
            # Paginação
            start_idx = page * self.frontend.items_per_page
            end_idx = start_idx + self.frontend.items_per_page
            page_channels = channels[start_idx:end_idx]
            
            keyboard = types.InlineKeyboardMarkup(row_width=1)
            
            # Adiciona canais da página atual
            for channel in page_channels:
                channel_name = self.frontend.truncate_text(channel['name'], 32)
                btn_text = f"📺 {channel_name}"
                
                # Botões para cada canal (play e adicionar ao M3U)
                btn_row = []
                btn_row.append(types.InlineKeyboardButton(
                    btn_text, 
                    callback_data=f"canal_play_{channel['stream_id']}"
                ))
                btn_row.append(types.InlineKeyboardButton(
                    "📥", 
                    callback_data=f"canal_add_{channel['stream_id']}"
                ))
                keyboard.row(*btn_row)
            
            # Botões de navegação
            nav_buttons = self.frontend.create_pagination_buttons(
                page, len(channels), "canal_list", category_id
            )
            if nav_buttons:
                keyboard.row(*nav_buttons)
            
            # Botão voltar
            btn_back = types.InlineKeyboardButton("🔙 Categorias", callback_data="menu_canais")
            keyboard.add(btn_back)
            
            # Texto com informações
            total_pages = (len(channels) + self.frontend.items_per_page - 1) // self.frontend.items_per_page
            text = f"""
📺 **CANAIS DE TV**

📊 **Página {page + 1} de {total_pages}**
📺 **Total: {len(channels)} canais**
📥 **Use o botão 📥 para adicionar ao M3U**

Escolha um canal:
            """
            
            try:
                self.bot.edit_message_text(text, chat_id, message_id, reply_markup=keyboard, parse_mode='Markdown')
            except Exception as e:
                print(f"Error editing channels message: {e}")
                try:
                    self.bot.delete_message(chat_id, message_id)
                except:
                    pass
                self.bot.send_message(chat_id, text, reply_markup=keyboard, parse_mode='Markdown')
            
        except Exception as e:
            print(f"Error showing channels: {e}")
            keyboard = self.frontend.create_error_message("Erro ao carregar canais", "menu_canais")
            text = "❌ Erro ao carregar canais. Tente novamente."
            try:
                self.bot.edit_message_text(text, chat_id, message_id, reply_markup=keyboard)
            except:
                self.bot.send_message(chat_id, text, reply_markup=keyboard)
    
    def play_channel(self, chat_id, message_id, config, stream_id):
        """Reproduz um canal"""
        try:
            channels = self.get_channels(config)
            channel = next((ch for ch in channels if str(ch['stream_id']) == str(stream_id)), None)
            
            if not channel:
                keyboard = self.frontend.create_error_message("Canal não encontrado", "menu_canais")
                text = "❌ Canal não encontrado."
                try:
                    self.bot.edit_message_text(text, chat_id, message_id, reply_markup=keyboard)
                except Exception as e:
                    print(f"Error editing channel not found: {e}")
                    self.bot.send_message(chat_id, text, reply_markup=keyboard)
                return
            
            keyboard = types.InlineKeyboardMarkup(row_width=2)
            
            btn_play = types.InlineKeyboardButton("▶️ Reproduzir", url=channel['play_url'])
            btn_add = types.InlineKeyboardButton("📥 Adicionar ao M3U", callback_data=f"canal_add_{stream_id}")
            btn_back = types.InlineKeyboardButton("🔙 Voltar", callback_data="canal_list_all_0")
            
            keyboard.row(btn_play, btn_add)
            keyboard.add(btn_back)
            
            # Informações do canal
            text = f"""
📺 **{channel['name']}**

🆔 **Stream ID:** {channel['stream_id']}
📡 **Categoria:** {channel.get('category_name', 'Geral')}
🌐 **Servidor:** {config['server'].split('//')[1] if '//' in config['server'] else config['server']}

🔗 **URL de reprodução:**
`{channel['play_url']}`

**💡 Como reproduzir:**
• Clique em "▶️ Reproduzir" para abrir no player
• Use 📥 para adicionar ao M3U
• Copie a URL para usar em outro player
            """
            
            # Tenta enviar com imagem se disponível
            if channel.get('stream_icon') and channel['stream_icon'].startswith('http'):
                try:
                    self.bot.delete_message(chat_id, message_id)
                    self.bot.send_photo(
                        chat_id, 
                        channel['stream_icon'],
                        caption=text,
                        reply_markup=keyboard,
                        parse_mode='Markdown'
                    )
                    return
                except Exception as img_error:
                    print(f"Error sending image: {img_error}")
            
            try:
                self.bot.edit_message_text(text, chat_id, message_id, reply_markup=keyboard, parse_mode='Markdown')
            except Exception as e:
                print(f"Error editing play channel message: {e}")
                try:
                    self.bot.delete_message(chat_id, message_id)
                except:
                    pass
                self.bot.send_message(chat_id, text, reply_markup=keyboard, parse_mode='Markdown')
            
        except Exception as e:
            print(f"Error playing channel: {e}")
            keyboard = self.frontend.create_error_message("Erro ao carregar canal", "menu_canais")
            text = "❌ Erro ao carregar canal. Tente novamente."
            try:
                self.bot.edit_message_text(text, chat_id, message_id, reply_markup=keyboard)
            except:
                self.bot.send_message(chat_id, text, reply_markup=keyboard)
    
    def add_to_m3u(self, call, config, stream_id):
        """Adiciona canal ao M3U preservando categoria original"""
        try:
            channels = self.get_channels(config)
            channel = next((ch for ch in channels if str(ch['stream_id']) == str(stream_id)), None)
            
            if not channel:
                self.bot.answer_callback_query(call.id, "❌ Canal não encontrado!")
                return
            
            # Prepara dados do canal para seleção preservando categoria original
            channel_data = {
                'id': channel['stream_id'],
                'name': channel['name'],
                'logo': channel.get('stream_icon', ''),
                'container': channel.get('container_extension', 'ts'),
                'category': channel.get('category_name', 'Canais')  # Preserva categoria original
            }
            
            # Adiciona à seleção
            added = self.backend.add_to_selection(call.message.chat.id, 'channels', channel_data)
            
            if added:
                self.bot.answer_callback_query(call.id, f"📥 {channel['name']} adicionado ao M3U!")
            else:
                self.bot.answer_callback_query(call.id, f"ℹ️ {channel['name']} já está no M3U!")
                
        except Exception as e:
            print(f"Error adding to M3U: {e}")
            self.bot.answer_callback_query(call.id, "❌ Erro ao adicionar ao M3U")
    
    def handle_callback(self, call, config):
        """Manipula callbacks específicos dos canais"""
        if not config:
            self.bot.answer_callback_query(call.id, "❌ Configure uma playlist primeiro!")
            return
        
        chat_id = call.message.chat.id
        message_id = call.message.message_id
        data = call.data
        
        try:
            if data.startswith("canal_list_"):
                parts = data.split("_")
                if len(parts) >= 4:
                    category_id = parts[2]
                    page = int(parts[3])
                    self.show_channels(chat_id, message_id, config, category_id, page)
            
            elif data.startswith("canal_play_"):
                stream_id = data.split("_")[2]
                self.play_channel(chat_id, message_id, config, stream_id)
            
            elif data.startswith("canal_add_"):
                stream_id = data.split("_")[2]
                self.add_to_m3u(call, config, stream_id)
                
        except Exception as e:
            print(f"Error in channel callback: {e}")
            self.bot.answer_callback_query(call.id, "❌ Erro interno")
