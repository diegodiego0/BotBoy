import requests
from telebot import types
import json
import time

class SerieManager:
    def __init__(self, bot, backend, frontend):
        self.bot = bot
        self.backend = backend
        self.frontend = frontend
        
    def get_categories(self, config):
        """Obtém categorias de séries"""
        params = {
            'username': config['username'],
            'password': config['password'],
            'action': 'get_series_categories'
        }
        
        return self.backend.make_api_request(config, params) or []
    
    def get_series(self, config, category_id=None):
        """Obtém lista de séries"""
        params = {
            'username': config['username'],
            'password': config['password'],
            'action': 'get_series'
        }
        
        if category_id:
            params['category_id'] = category_id
        
        return self.backend.make_api_request(config, params) or []
    
    def get_episodes(self, config, series_id, season=None):
        """Obtém lista de episódios de uma série"""
        params = {
            'username': config['username'],
            'password': config['password'],
            'action': 'get_series_info',
            'series_id': series_id
        }
        
        series_info = self.backend.make_api_request(config, params) or {}
        
        if season:
            return series_info.get('episodes', {}).get(str(season), [])
        
        # Retorna todos os episódios de todas as temporadas
        all_episodes = []
        for season_num, episodes in series_info.get('episodes', {}).items():
            all_episodes.extend(episodes)
        
        return all_episodes
    
    def show_categories(self, chat_id, message_id, config):
        """Mostra categorias de séries com opção de adicionar categoria completa"""
        try:
            categories = self.get_categories(config)
            
            if not categories:
                keyboard = self.frontend.create_error_message("❌ Nenhuma categoria de séries encontrada.")
                text = "❌ Não foi possível carregar as categorias de séries."
                try:
                    self.bot.edit_message_text(text, chat_id, message_id, reply_markup=keyboard)
                except Exception as e:
                    print(f"Error editing message: {e}")
                    self.bot.send_message(chat_id, text, reply_markup=keyboard)
                return
            
            keyboard = types.InlineKeyboardMarkup(row_width=1)
            
            # Adiciona botão para todas as séries
            btn_all = types.InlineKeyboardButton("📺 Todas as Séries", callback_data="serie_list_all_0")
            keyboard.add(btn_all)
            
            # Adiciona categorias (máximo 12) com botões para navegar e adicionar categoria completa
            for i, category in enumerate(categories[:12]):
                category_name = self.frontend.truncate_text(category['category_name'], 25)
                
                # Linha com botão de navegação e botão de adicionar categoria completa
                btn_nav = types.InlineKeyboardButton(
                    f"📁 {category_name}", 
                    callback_data=f"serie_list_{category['category_id']}_0"
                )
                btn_add_all = types.InlineKeyboardButton(
                    "📥➕", 
                    callback_data=f"add_full_category_series_{category['category_id']}"
                )
                keyboard.row(btn_nav, btn_add_all)
            
            # Botão voltar
            btn_back = types.InlineKeyboardButton("🔙 Menu Principal", callback_data="menu_principal")
            keyboard.add(btn_back)
            
            text = f"""
📺 **CATEGORIAS DE SÉRIES**

📊 **{len(categories)} categorias encontradas**
🎯 **Navegação otimizada**

**💡 Como usar:**
• 📁 **Nome da categoria**: Navegar pelas séries
• 📥➕ **Adicionar categoria**: Adiciona todas as séries da categoria ao M3U

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
            print(f"Error showing series categories: {e}")
            keyboard = self.frontend.create_error_message("Erro ao carregar categorias")
            text = "❌ Erro ao carregar categorias. Tente novamente."
            try:
                self.bot.edit_message_text(text, chat_id, message_id, reply_markup=keyboard)
            except:
                self.bot.send_message(chat_id, text, reply_markup=keyboard)

    def show_episodes(self, chat_id, message_id, config, series_id, season=None, page=0):
        """Mostra episódios de uma série com opção de download"""
        try:
            episodes = self.get_episodes(config, series_id, season)
            
            if not episodes:
                keyboard = self.frontend.create_error_message("❌ Nenhum episódio encontrado.", "menu_series")
                text = "❌ Nenhum episódio encontrado para esta série."
                try:
                    self.bot.edit_message_text(text, chat_id, message_id, reply_markup=keyboard)
                except Exception as e:
                    print(f"Error editing no episodes message: {e}")
                    self.bot.send_message(chat_id, text, reply_markup=keyboard)
                return
            
            # Paginação
            start_idx = page * self.frontend.items_per_page
            end_idx = start_idx + self.frontend.items_per_page
            page_episodes = episodes[start_idx:end_idx]
            
            keyboard = types.InlineKeyboardMarkup(row_width=1)
            
            # Adiciona episódios da página atual
            for episode in page_episodes:
                ep_title = episode.get('title', f"Episódio {episode.get('episode_num', '?')}")
                btn_text = f"▶️ S{episode.get('season', '?')}E{episode.get('episode_num', '?')} - {self.frontend.truncate_text(ep_title, 25)}"
                
                # Botões para cada episódio (play, adicionar ao M3U, download)
                btn_row = []
                btn_row.append(types.InlineKeyboardButton(
                    btn_text, 
                    callback_data=f"serie_play_{episode['id']}"
                ))
                btn_row.append(types.InlineKeyboardButton(
                    "📥", 
                    callback_data=f"serie_add_episode_{episode['id']}"
                ))
                btn_row.append(types.InlineKeyboardButton(
                    "💾", 
                    callback_data=f"download_options_episode_{episode['id']}_{ep_title}"
                ))
                keyboard.row(*btn_row)
            
            # Botões de navegação
            nav_buttons = self.frontend.create_pagination_buttons(
                page, len(episodes), "serie_episodes", series_id
            )
            if nav_buttons:
                keyboard.row(*nav_buttons)
            
            # Botão voltar
            btn_back = types.InlineKeyboardButton("🔙 Séries", callback_data="menu_series")
            keyboard.add(btn_back)
            
            # Texto com informações
            total_pages = (len(episodes) + self.frontend.items_per_page - 1) // self.frontend.items_per_page
            text = f"""
📺 **EPISÓDIOS DA SÉRIE**

📊 **Página {page + 1} de {total_pages}**
📺 **Total: {len(episodes)} episódios**
📥 **Use o botão 📥 para adicionar ao M3U**
💾 **Use o botão 💾 para fazer download**

Escolha um episódio:
            """
            
            try:
                self.bot.edit_message_text(text, chat_id, message_id, reply_markup=keyboard, parse_mode='Markdown')
            except Exception as e:
                print(f"Error editing episodes message: {e}")
                try:
                    self.bot.delete_message(chat_id, message_id)
                except:
                    pass
                self.bot.send_message(chat_id, text, reply_markup=keyboard, parse_mode='Markdown')
            
        except Exception as e:
            print(f"Error showing episodes: {e}")
            keyboard = self.frontend.create_error_message("Erro ao carregar episódios", "menu_series")
            text = "❌ Erro ao carregar episódios. Tente novamente."
            try:
                self.bot.edit_message_text(text, chat_id, message_id, reply_markup=keyboard)
            except:
                self.bot.send_message(chat_id, text, reply_markup=keyboard)

    def handle_callback(self, call, config):
        """Manipula callbacks específicos das séries"""
        if not config:
            self.bot.answer_callback_query(call.id, "❌ Configure uma playlist primeiro!")
            return
        
        chat_id = call.message.chat.id
        message_id = call.message.message_id
        data = call.data
        
        try:
            if data.startswith("serie_list_"):
                parts = data.split("_")
                if len(parts) >= 4:
                    category_id = parts[2]
                    page = int(parts[3])
                    self.show_series(chat_id, message_id, config, category_id, page)
            
            elif data.startswith("serie_episodes_"):
                series_id = data.split("_")[2]
                self.show_episodes(chat_id, message_id, config, series_id)
            
            elif data.startswith("serie_play_"):
                episode_id = data.split("_")[2]
                self.play_episode(chat_id, message_id, config, episode_id)
            
            elif data.startswith("serie_add_"):
                series_id = data.split("_")[2]
                self.add_to_m3u(call, config, series_id)
            
            elif data.startswith("serie_add_episode_"):
                episode_id = data.split("_")[3]
                self.add_episode_to_m3u(call, config, episode_id)
                
        except Exception as e:
            print(f"Error in series callback: {e}")
            self.bot.answer_callback_query(call.id, "❌ Erro interno")
