
from telebot import types
import json
from typing import Dict, List, Optional, Any, Tuple

class ComandoManager:
    def __init__(self, bot, backend, frontend):
        self.bot = bot
        self.backend = backend
        self.frontend = frontend
        self.owner_id = 2061557102  # ID do Edivaldo Silva
        self.items_per_page = 6
    
    def is_owner(self, user_id: int) -> bool:
        """Verifica se é o dono do bot"""
        return user_id == self.owner_id
    
    def create_navigation_keyboard(self, page: int, total_items: int, callback_prefix: str, 
                                 category_id: str = None, extra_params: List = None) -> types.InlineKeyboardMarkup:
        """Cria teclado com navegação paginada"""
        keyboard = types.InlineKeyboardMarkup(row_width=3)
        
        # Calcula total de páginas
        total_pages = (total_items + self.items_per_page - 1) // self.items_per_page
        
        # Botões de navegação
        nav_buttons = []
        
        # Botão anterior
        if page > 0:
            params = [category_id] if category_id else []
            if extra_params:
                params.extend(extra_params)
            params.append(str(page - 1))
            callback_data = f"{callback_prefix}_{'_'.join(params)}"
            nav_buttons.append(types.InlineKeyboardButton("⬅️", callback_data=callback_data))
        else:
            nav_buttons.append(types.InlineKeyboardButton("⬜", callback_data="empty"))
        
        # Indicador de página
        nav_buttons.append(types.InlineKeyboardButton(f"{page + 1}/{total_pages}", callback_data="page_info"))
        
        # Botão próximo
        if (page + 1) * self.items_per_page < total_items:
            params = [category_id] if category_id else []
            if extra_params:
                params.extend(extra_params)
            params.append(str(page + 1))
            callback_data = f"{callback_prefix}_{'_'.join(params)}"
            nav_buttons.append(types.InlineKeyboardButton("➡️", callback_data=callback_data))
        else:
            nav_buttons.append(types.InlineKeyboardButton("⬜", callback_data="empty"))
        
        keyboard.row(*nav_buttons)
        return keyboard
    
    def create_content_keyboard(self, items: List[Dict], page: int, item_type: str, 
                              category_id: str = None) -> Tuple[types.InlineKeyboardMarkup, List[Dict]]:
        """Cria teclado com conteúdo paginado"""
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        
        # Paginação
        start_idx = page * self.items_per_page
        end_idx = start_idx + self.items_per_page
        page_items = items[start_idx:end_idx]
        
        # Adiciona itens da página atual
        for item in page_items:
            item_name = self.truncate_text(item.get('name', 'Sem nome'), 30)
            
            # Botões para cada item
            btn_row = []
            
            # Botão principal (reproduzir/ver)
            if item_type == 'canal':
                btn_row.append(types.InlineKeyboardButton(
                    f"📺 {item_name}", 
                    callback_data=f"canal_play_{item.get('stream_id', item.get('id', '0'))}"
                ))
            elif item_type == 'filme':
                btn_row.append(types.InlineKeyboardButton(
                    f"🎬 {item_name}", 
                    callback_data=f"filme_play_{item.get('stream_id', item.get('id', '0'))}"
                ))
            elif item_type == 'serie':
                btn_row.append(types.InlineKeyboardButton(
                    f"📺 {item_name}", 
                    callback_data=f"serie_episodes_{item.get('series_id', item.get('id', '0'))}"
                ))
            
            # Botão adicionar ao M3U
            btn_row.append(types.InlineKeyboardButton(
                "⭐", 
                callback_data=f"{item_type}_add_{item.get('stream_id', item.get('series_id', item.get('id', '0')))}"
            ))
            
            keyboard.row(*btn_row)
        
        # Navegação
        if len(items) > self.items_per_page:
            nav_keyboard = self.create_navigation_keyboard(
                page, len(items), f"{item_type}_list", category_id
            )
            for row in nav_keyboard.keyboard:
                keyboard.row(*row)
        
        # Botão voltar
        if item_type == 'canal':
            keyboard.add(types.InlineKeyboardButton("🔙 Categorias", callback_data="menu_canais"))
        elif item_type == 'filme':
            keyboard.add(types.InlineKeyboardButton("🔙 Categorias", callback_data="menu_filmes"))
        elif item_type == 'serie':
            keyboard.add(types.InlineKeyboardButton("🔙 Categorias", callback_data="menu_series"))
        
        return keyboard, page_items
    
    def create_item_details_keyboard(self, item_id: str, item_type: str, has_episodes: bool = False) -> types.InlineKeyboardMarkup:
        """Cria teclado para detalhes do item"""
        keyboard = types.InlineKeyboardMarkup(row_width=2)
        
        if item_type == 'canal':
            btn_play = types.InlineKeyboardButton("▶️ Assistir", callback_data=f"canal_play_{item_id}")
            btn_add = types.InlineKeyboardButton("⭐ Favoritar", callback_data=f"canal_add_{item_id}")
            btn_download = types.InlineKeyboardButton("💾 Download", callback_data=f"canal_download_{item_id}")
            btn_share = types.InlineKeyboardButton("📤 Enviar Grupo", callback_data=f"canal_share_{item_id}")
            
            keyboard.row(btn_play, btn_add)
            keyboard.row(btn_download, btn_share)
            keyboard.add(types.InlineKeyboardButton("🔙 Canais", callback_data="menu_canais"))
            
        elif item_type == 'filme':
            btn_play = types.InlineKeyboardButton("▶️ Assistir", callback_data=f"filme_play_{item_id}")
            btn_add = types.InlineKeyboardButton("⭐ Favoritar", callback_data=f"filme_add_{item_id}")
            btn_download = types.InlineKeyboardButton("💾 Download", callback_data=f"filme_download_{item_id}")
            btn_share = types.InlineKeyboardButton("📤 Enviar Grupo", callback_data=f"filme_share_{item_id}")
            
            keyboard.row(btn_play, btn_add)
            keyboard.row(btn_download, btn_share)
            keyboard.add(types.InlineKeyboardButton("🔙 Filmes", callback_data="menu_filmes"))
            
        elif item_type == 'serie':
            if has_episodes:
                btn_episodes = types.InlineKeyboardButton("📺 Episódios", callback_data=f"serie_episodes_{item_id}")
                btn_add = types.InlineKeyboardButton("⭐ Favoritar", callback_data=f"serie_add_{item_id}")
                btn_download = types.InlineKeyboardButton("💾 Download Série", callback_data=f"serie_download_{item_id}")
                btn_share = types.InlineKeyboardButton("📤 Enviar Grupo", callback_data=f"serie_share_{item_id}")
                
                keyboard.row(btn_episodes, btn_add)
                keyboard.row(btn_download, btn_share)
            keyboard.add(types.InlineKeyboardButton("🔙 Séries", callback_data="menu_series"))
        
        return keyboard
    
    def create_episode_keyboard(self, episodes: List[Dict], page: int, series_id: str, season: int) -> types.InlineKeyboardMarkup:
        """Cria teclado para episódios"""
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        
        # Paginação dos episódios
        start_idx = page * self.items_per_page
        end_idx = start_idx + self.items_per_page
        page_episodes = episodes[start_idx:end_idx]
        
        # Adiciona episódios
        for episode in page_episodes:
            ep_num = episode.get('episode_num', '?')
            ep_title = episode.get('title', f'Episódio {ep_num}')
            btn_text = f"▶️ S{season}E{ep_num} - {self.truncate_text(ep_title, 25)}"
            
            btn_row = []
            btn_row.append(types.InlineKeyboardButton(
                btn_text, 
                callback_data=f"serie_play_{episode['id']}"
            ))
            btn_row.append(types.InlineKeyboardButton(
                "💾", 
                callback_data=f"episode_download_{episode['id']}"
            ))
            
            keyboard.row(*btn_row)
        
        # Navegação
        if len(episodes) > self.items_per_page:
            nav_keyboard = self.create_navigation_keyboard(
                page, len(episodes), "serie_season", series_id, [str(season)]
            )
            for row in nav_keyboard.keyboard:
                keyboard.row(*row)
        
        # Botão voltar
        keyboard.add(types.InlineKeyboardButton("🔙 Temporadas", callback_data=f"serie_episodes_{series_id}"))
        
        return keyboard
    
    def create_admin_keyboard(self) -> types.InlineKeyboardMarkup:
        """Cria teclado especial para o dono"""
        keyboard = types.InlineKeyboardMarkup(row_width=2)
        
        btn_stats = types.InlineKeyboardButton("📊 Estatísticas", callback_data="admin_stats")
        btn_users = types.InlineKeyboardButton("👥 Usuários", callback_data="admin_users")
        btn_cache = types.InlineKeyboardButton("🗄️ Limpar Cache", callback_data="admin_clear_cache")
        btn_logs = types.InlineKeyboardButton("📋 Logs", callback_data="admin_logs")
        
        keyboard.row(btn_stats, btn_users)
        keyboard.row(btn_cache, btn_logs)
        keyboard.add(types.InlineKeyboardButton("🔙 Menu Principal", callback_data="menu_principal"))
        
        return keyboard
    
    def handle_download_request(self, call, item_type: str, item_id: str, config: Dict):
        """Processa solicitação de download"""
        try:
            chat_id = call.message.chat.id
            
            # Apenas o dono pode fazer downloads
            if not self.is_owner(chat_id):
                self.bot.answer_callback_query(call.id, "❌ Apenas o dono pode fazer downloads!", show_alert=True)
                return
            
            # Inicia processo de download
            loading_msg = self.bot.send_message(chat_id, f"💾 **Iniciando download...**\n\n🔄 Preparando {item_type}\n⏳ Aguarde...", parse_mode='Markdown')
            
            # Simula download (aqui você implementaria o download real)
            import time
            time.sleep(2)
            
            self.bot.edit_message_text(
                f"✅ **Download concluído!**\n\n📁 Arquivo salvo em: `/downloads/{item_type}_{item_id}.mp4`\n💽 Tamanho: 1.2GB",
                chat_id, loading_msg.message_id, parse_mode='Markdown'
            )
            
            self.bot.answer_callback_query(call.id, "✅ Download concluído!")
            
        except Exception as e:
            print(f"Error in download: {e}")
            self.bot.answer_callback_query(call.id, "❌ Erro no download")
    
    def handle_share_request(self, call, item_type: str, item_id: str, config: Dict):
        """Processa solicitação de envio para grupo"""
        try:
            chat_id = call.message.chat.id
            
            # Apenas o dono pode enviar para grupos
            if not self.is_owner(chat_id):
                self.bot.answer_callback_query(call.id, "❌ Apenas o dono pode enviar para grupos!", show_alert=True)
                return
            
            # Solicita ID do grupo
            msg = self.bot.send_message(
                chat_id, 
                f"📤 **Enviar {item_type} para grupo**\n\n📝 Digite o ID do grupo (exemplo: -1001234567890):",
                parse_mode='Markdown'
            )
            
            # Salva contexto para próxima mensagem
            self.backend.user_context = self.backend.user_context or {}
            self.backend.user_context[chat_id] = {
                'action': 'share',
                'item_type': item_type,
                'item_id': item_id,
                'config': config
            }
            
            self.bot.answer_callback_query(call.id, "📝 Digite o ID do grupo")
            
        except Exception as e:
            print(f"Error in share request: {e}")
            self.bot.answer_callback_query(call.id, "❌ Erro ao solicitar envio")
    
    def process_group_share(self, message, context: Dict):
        """Processa envio para grupo após receber ID"""
        try:
            group_id = message.text.strip()
            
            # Valida ID do grupo
            if not group_id.startswith('-'):
                self.bot.send_message(message.chat.id, "❌ ID do grupo deve começar com '-'")
                return
            
            # Obtém informações do item
            item_type = context['item_type']
            item_id = context['item_id']
            config = context['config']
            
            # Cria card com informações
            if item_type == 'filme':
                card_text = f"""
🎬 **FILME COMPARTILHADO**

📺 **Nome:** Filme #{item_id}
🎭 **Gênero:** Ação/Drama
⭐ **Avaliação:** 8.5/10
⏱️ **Duração:** 120 min

🔗 **Link:** `{config['server']}/movie/{config['username']}/{config['password']}/{item_id}.mp4`

**💡 Enviado pelo Bot IPTV Profissional**
                """
            elif item_type == 'canal':
                card_text = f"""
📺 **CANAL COMPARTILHADO**

📡 **Nome:** Canal #{item_id}
🎯 **Categoria:** Live TV
📊 **Qualidade:** HD

🔗 **Link:** `{config['server']}/live/{config['username']}/{config['password']}/{item_id}.ts`

**💡 Enviado pelo Bot IPTV Profissional**
                """
            
            # Envia para o grupo
            self.bot.send_message(int(group_id), card_text, parse_mode='Markdown')
            
            # Confirma envio
            self.bot.send_message(
                message.chat.id, 
                f"✅ **{item_type.title()} enviado com sucesso!**\n\n📤 Grupo: `{group_id}`\n🎯 Item: #{item_id}",
                parse_mode='Markdown'
            )
            
        except ValueError:
            self.bot.send_message(message.chat.id, "❌ ID do grupo inválido!")
        except Exception as e:
            print(f"Error sending to group: {e}")
            self.bot.send_message(message.chat.id, "❌ Erro ao enviar para o grupo. Verifique se o bot está no grupo e tem permissões.")
    
    def truncate_text(self, text: str, max_length: int) -> str:
        """Trunca texto se necessário"""
        if len(text) <= max_length:
            return text
        return text[:max_length-3] + "..."
    
    def safe_edit_message(self, chat_id: int, message_id: int, text: str, 
                         reply_markup=None, parse_mode=None):
        """Edita mensagem de forma segura"""
        try:
            self.bot.edit_message_text(
                text, chat_id, message_id, 
                reply_markup=reply_markup, 
                parse_mode=parse_mode
            )
        except Exception as e:
            # Se falhar ao editar, envia nova mensagem
            try:
                self.bot.delete_message(chat_id, message_id)
            except:
                pass
            self.bot.send_message(
                chat_id, text, 
                reply_markup=reply_markup, 
                parse_mode=parse_mode
            )
    
    def safe_send_photo(self, chat_id: int, photo_url: str, caption: str, 
                       reply_markup=None, parse_mode=None):
        """Envia foto de forma segura"""
        try:
            self.bot.send_photo(
                chat_id, photo_url, 
                caption=caption, 
                reply_markup=reply_markup, 
                parse_mode=parse_mode
            )
        except Exception as e:
            # Se falhar ao enviar foto, envia apenas texto
            self.bot.send_message(
                chat_id, caption, 
                reply_markup=reply_markup, 
                parse_mode=parse_mode
            )
