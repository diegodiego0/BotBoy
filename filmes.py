import requests
from telebot import types
import json
import time

class FilmeManager:
    def __init__(self, bot, backend, frontend):
        self.bot = bot
        self.backend = backend
        self.frontend = frontend
        
    def get_categories(self, config):
        """Obtém categorias de filmes"""
        params = {
            'username': config['username'],
            'password': config['password'],
            'action': 'get_vod_categories'
        }
        
        return self.backend.make_api_request(config, params) or []
    
    def get_movies(self, config, category_id=None):
        """Obtém lista de filmes"""
        params = {
            'username': config['username'],
            'password': config['password'],
            'action': 'get_vod_streams'
        }
        
        if category_id:
            params['category_id'] = category_id
        
        movies = self.backend.make_api_request(config, params) or []
        
        # Adiciona URL de reprodução e preserva categoria original
        categories = self.get_categories(config)
        category_map = {str(cat.get('category_id')): cat.get('category_name', 'Filmes') for cat in categories}
        
        for movie in movies:
            movie['play_url'] = f"{config['server']}/movie/{config['username']}/{config['password']}/{movie['stream_id']}.{movie.get('container_extension', 'mp4')}"
            # Preserva categoria original
            if not movie.get('category_name') and category_id:
                movie['category_name'] = category_map.get(str(category_id), 'Filmes')
        
        return movies
    
    def show_categories(self, chat_id, message_id, config):
        """Mostra categorias de filmes com opção de adicionar categoria completa"""
        try:
            categories = self.get_categories(config)
            
            if not categories:
                keyboard = self.frontend.create_error_message("❌ Nenhuma categoria de filmes encontrada.")
                text = "❌ Não foi possível carregar as categorias de filmes."
                try:
                    self.bot.edit_message_text(text, chat_id, message_id, reply_markup=keyboard)
                except Exception as e:
                    print(f"Error editing message: {e}")
                    self.bot.send_message(chat_id, text, reply_markup=keyboard)
                return
            
            keyboard = types.InlineKeyboardMarkup(row_width=1)
            
            # Adiciona botão para todos os filmes
            btn_all = types.InlineKeyboardButton("🎬 Todos os Filmes", callback_data="filme_list_all_0")
            keyboard.add(btn_all)
            
            # Adiciona categorias (máximo 12) com botões para navegar e adicionar categoria completa
            for i, category in enumerate(categories[:12]):
                category_name = self.frontend.truncate_text(category['category_name'], 25)
                
                # Linha com botão de navegação e botão de adicionar categoria completa
                btn_nav = types.InlineKeyboardButton(
                    f"📁 {category_name}", 
                    callback_data=f"filme_list_{category['category_id']}_0"
                )
                btn_add_all = types.InlineKeyboardButton(
                    "📥➕", 
                    callback_data=f"add_full_category_movies_{category['category_id']}"
                )
                keyboard.row(btn_nav, btn_add_all)
            
            # Botão voltar
            btn_back = types.InlineKeyboardButton("🔙 Menu Principal", callback_data="menu_principal")
            keyboard.add(btn_back)
            
            text = f"""
🎬 **CATEGORIAS DE FILMES**

📊 **{len(categories)} categorias encontradas**
🎯 **Navegação otimizada**

**💡 Como usar:**
• 📁 **Nome da categoria**: Navegar pelos filmes
• 📥➕ **Adicionar categoria**: Adiciona todos os filmes da categoria ao M3U

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
            print(f"Error showing movie categories: {e}")
            keyboard = self.frontend.create_error_message("Erro ao carregar categorias")
            text = "❌ Erro ao carregar categorias. Tente novamente."
            try:
                self.bot.edit_message_text(text, chat_id, message_id, reply_markup=keyboard)
            except:
                self.bot.send_message(chat_id, text, reply_markup=keyboard)

    def show_movies(self, chat_id, message_id, config, category_id, page=0):
        """Mostra lista de filmes com paginação"""
        try:
            if category_id == "all":
                movies = self.get_movies(config)
            else:
                movies = self.get_movies(config, category_id)
            
            if not movies:
                keyboard = self.frontend.create_error_message("❌ Nenhum filme encontrado.", "menu_filmes")
                text = "❌ Nenhum filme encontrado nesta categoria."
                try:
                    self.bot.edit_message_text(text, chat_id, message_id, reply_markup=keyboard)
                except Exception as e:
                    print(f"Error editing no movies message: {e}")
                    self.bot.send_message(chat_id, text, reply_markup=keyboard)
                return
            
            # Paginação
            start_idx = page * self.frontend.items_per_page
            end_idx = start_idx + self.frontend.items_per_page
            page_movies = movies[start_idx:end_idx]
            
            keyboard = types.InlineKeyboardMarkup(row_width=1)
            
            # Adiciona filmes da página atual
            for movie in page_movies:
                movie_name = self.frontend.truncate_text(movie['name'], 28)
                btn_text = f"🎬 {movie_name}"
                
                # Botões para cada filme (play, adicionar ao M3U, download)
                btn_row = []
                btn_row.append(types.InlineKeyboardButton(
                    btn_text, 
                    callback_data=f"filme_play_{movie['stream_id']}"
                ))
                btn_row.append(types.InlineKeyboardButton(
                    "📥", 
                    callback_data=f"filme_add_{movie['stream_id']}"
                ))
                btn_row.append(types.InlineKeyboardButton(
                    "💾", 
                    callback_data=f"download_options_movie_{movie['stream_id']}_{movie['name']}"
                ))
                keyboard.row(*btn_row)
            
            # Botões de navegação
            nav_buttons = self.frontend.create_pagination_buttons(
                page, len(movies), "filme_list", category_id
            )
            if nav_buttons:
                keyboard.row(*nav_buttons)
            
            # Botão voltar
            btn_back = types.InlineKeyboardButton("🔙 Categorias", callback_data="menu_filmes")
            keyboard.add(btn_back)
            
            # Texto com informações
            total_pages = (len(movies) + self.frontend.items_per_page - 1) // self.frontend.items_per_page
            text = f"""
🎬 **FILMES**

📊 **Página {page + 1} de {total_pages}**
🎬 **Total: {len(movies)} filmes**
📥 **Use o botão 📥 para adicionar ao M3U**
💾 **Use o botão 💾 para fazer download**

Escolha um filme:
            """
            
            try:
                self.bot.edit_message_text(text, chat_id, message_id, reply_markup=keyboard, parse_mode='Markdown')
            except Exception as e:
                print(f"Error editing movies message: {e}")
                try:
                    self.bot.delete_message(chat_id, message_id)
                except:
                    pass
                self.bot.send_message(chat_id, text, reply_markup=keyboard, parse_mode='Markdown')
            
        except Exception as e:
            print(f"Error showing movies: {e}")
            keyboard = self.frontend.create_error_message("Erro ao carregar filmes", "menu_filmes")
            text = "❌ Erro ao carregar filmes. Tente novamente."
            try:
                self.bot.edit_message_text(text, chat_id, message_id, reply_markup=keyboard)
            except:
                self.bot.send_message(chat_id, text, reply_markup=keyboard)
    
    def play_movie(self, chat_id, message_id, config, stream_id):
        """Reproduz um filme"""
        try:
            movies = self.get_movies(config)
            movie = next((mv for mv in movies if str(mv['stream_id']) == str(stream_id)), None)
            
            if not movie:
                keyboard = self.frontend.create_error_message("Filme não encontrado", "menu_filmes")
                text = "❌ Filme não encontrado."
                try:
                    self.bot.edit_message_text(text, chat_id, message_id, reply_markup=keyboard)
                except Exception as e:
                    print(f"Error editing movie not found: {e}")
                    self.bot.send_message(chat_id, text, reply_markup=keyboard)
                return
            
            keyboard = types.InlineKeyboardMarkup(row_width=2)
            
            btn_play = types.InlineKeyboardButton("▶️ Reproduzir", url=movie['play_url'])
            btn_add = types.InlineKeyboardButton("📥 Adicionar ao M3U", callback_data=f"filme_add_{stream_id}")
            btn_download = types.InlineKeyboardButton("💾 Download", callback_data=f"download_options_movie_{stream_id}_{movie['name']}")
            btn_back = types.InlineKeyboardButton("🔙 Voltar", callback_data="filme_list_all_0")
            
            keyboard.row(btn_play, btn_add)
            keyboard.row(btn_download)
            keyboard.add(btn_back)
            
            # Informações do filme
            text = f"""
🎬 **{movie['name']}**

🆔 **Stream ID:** {movie['stream_id']}
📡 **Categoria:** {movie.get('category_name', 'Geral')}
🌐 **Servidor:** {config['server'].split('//')[1] if '//' in config['server'] else config['server']}

🔗 **URL de reprodução:**
`{movie['play_url']}`

**💡 Como reproduzir:**
• Clique em "▶️ Reproduzir" para abrir no player
• Use 📥 para adicionar ao M3U
• Use 💾 para baixar o filme
• Copie a URL para usar em outro player
            """
            
            # Tenta enviar com imagem se disponível
            if movie.get('stream_icon') and movie['stream_icon'].startswith('http'):
                try:
                    self.bot.delete_message(chat_id, message_id)
                    self.bot.send_photo(
                        chat_id, 
                        movie['stream_icon'],
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
                print(f"Error editing play movie message: {e}")
                try:
                    self.bot.delete_message(chat_id, message_id)
                except:
                    pass
                self.bot.send_message(chat_id, text, reply_markup=keyboard, parse_mode='Markdown')
            
        except Exception as e:
            print(f"Error playing movie: {e}")
            keyboard = self.frontend.create_error_message("Erro ao carregar filme", "menu_filmes")
            text = "❌ Erro ao carregar filme. Tente novamente."
            try:
                self.bot.edit_message_text(text, chat_id, message_id, reply_markup=keyboard)
            except:
                self.bot.send_message(chat_id, text, reply_markup=keyboard)
    
    def add_to_m3u(self, call, config, stream_id):
        """Adiciona filme ao M3U preservando categoria original"""
        try:
            movies = self.get_movies(config)
            movie = next((mv for mv in movies if str(mv['stream_id']) == str(stream_id)), None)
            
            if not movie:
                self.bot.answer_callback_query(call.id, "❌ Filme não encontrado!")
                return
            
            # Prepara dados do filme para seleção preservando categoria original
            movie_data = {
                'id': movie['stream_id'],
                'name': movie['name'],
                'logo': movie.get('stream_icon', ''),
                'container': movie.get('container_extension', 'mp4'),
                'category': movie.get('category_name', 'Filmes')  # Preserva categoria original
            }
            
            # Adiciona à seleção
            added = self.backend.add_to_selection(call.message.chat.id, 'movies', movie_data)
            
            if added:
                self.bot.answer_callback_query(call.id, f"📥 {movie['name']} adicionado ao M3U!")
            else:
                self.bot.answer_callback_query(call.id, f"ℹ️ {movie['name']} já está no M3U!")
                
        except Exception as e:
            print(f"Error adding to M3U: {e}")
            self.bot.answer_callback_query(call.id, "❌ Erro ao adicionar ao M3U")
    
    def handle_callback(self, call, config):
        """Manipula callbacks específicos dos filmes"""
        if not config:
            self.bot.answer_callback_query(call.id, "❌ Configure uma playlist primeiro!")
            return
        
        chat_id = call.message.chat.id
        message_id = call.message.message_id
        data = call.data
        
        try:
            if data.startswith("filme_list_"):
                parts = data.split("_")
                if len(parts) >= 4:
                    category_id = parts[2]
                    page = int(parts[3])
                    self.show_movies(chat_id, message_id, config, category_id, page)
            
            elif data.startswith("filme_play_"):
                stream_id = data.split("_")[2]
                self.play_movie(chat_id, message_id, config, stream_id)
            
            elif data.startswith("filme_add_"):
                stream_id = data.split("_")[2]
                self.add_to_m3u(call, config, stream_id)
                
        except Exception as e:
            print(f"Error in movie callback: {e}")
            self.bot.answer_callback_query(call.id, "❌ Erro interno")
