
import os
import requests
import threading
import time
from urllib.parse import urlparse
from telebot import types

class DownloadManager:
    def __init__(self, bot, backend):
        self.bot = bot
        self.backend = backend
        self.download_dir = "downloads"
        self.max_file_size = 2 * 1024 * 1024 * 1024  # 2GB limite
        
        # Cria diretório de downloads se não existir
        if not os.path.exists(self.download_dir):
            os.makedirs(self.download_dir)
    
    def is_download_allowed(self, user_id):
        """Verifica se o usuário pode fazer download (apenas owner)"""
        return self.backend.is_owner(user_id)
    
    def get_file_formats(self, config, stream_id, content_type='movie'):
        """Obtém formatos disponíveis para download"""
        try:
            # Para filmes
            if content_type == 'movie':
                params = {
                    'username': config['username'],
                    'password': config['password'],
                    'action': 'get_movie_info',
                    'movie_id': stream_id
                }
            # Para episódios de séries
            else:
                params = {
                    'username': config['username'],
                    'password': config['password'],
                    'action': 'get_episode_info',
                    'episode_id': stream_id
                }
            
            info = self.backend.make_api_request(config, params)
            
            if info and 'movie_data' in info:
                # Formatos disponíveis
                formats = []
                movie_data = info['movie_data']
                
                # Formato padrão
                if movie_data.get('container_extension'):
                    formats.append({
                        'quality': 'Original',
                        'format': movie_data['container_extension'],
                        'size': 'Tamanho original'
                    })
                
                # Formatos adicionais simulados (baseados no container)
                container = movie_data.get('container_extension', 'mp4')
                if container in ['mkv', 'mp4', 'avi']:
                    formats.extend([
                        {'quality': 'HD 720p', 'format': 'mp4', 'size': '~1.5GB'},
                        {'quality': 'Full HD 1080p', 'format': 'mp4', 'size': '~3GB'},
                        {'quality': 'SD 480p', 'format': 'mp4', 'size': '~800MB'}
                    ])
                
                return formats
            
            return [{'quality': 'Padrão', 'format': 'mp4', 'size': 'Tamanho variável'}]
            
        except Exception as e:
            print(f"Error getting file formats: {e}")
            return [{'quality': 'Padrão', 'format': 'mp4', 'size': 'Tamanho variável'}]
    
    def show_download_options(self, chat_id, message_id, config, stream_id, content_type, item_name):
        """Mostra opções de download"""
        try:
            if not self.is_download_allowed(chat_id):
                keyboard = types.InlineKeyboardMarkup()
                btn_back = types.InlineKeyboardButton("🔙 Voltar", callback_data=f"{content_type}_play_{stream_id}")
                keyboard.add(btn_back)
                
                text = "❌ **Download restrito!**\n\nApenas o proprietário do bot pode fazer downloads."
                
                self.bot.edit_message_text(text, chat_id, message_id, reply_markup=keyboard, parse_mode='Markdown')
                return
            
            formats = self.get_file_formats(config, stream_id, content_type)
            
            keyboard = types.InlineKeyboardMarkup(row_width=1)
            
            for i, fmt in enumerate(formats):
                btn_text = f"📥 {fmt['quality']} ({fmt['format'].upper()}) - {fmt['size']}"
                callback_data = f"download_start_{content_type}_{stream_id}_{i}"
                keyboard.add(types.InlineKeyboardButton(btn_text, callback_data=callback_data))
            
            # Botão voltar
            btn_back = types.InlineKeyboardButton("🔙 Voltar", callback_data=f"{content_type}_play_{stream_id}")
            keyboard.add(btn_back)
            
            text = f"""
💾 **OPÇÕES DE DOWNLOAD**

🎬 **{item_name}**

**📋 Escolha o formato:**
• Diferentes qualidades disponíveis
• Download direto para você
• Arquivo será removido após envio

**⚠️ Importante:**
• Downloads podem demorar alguns minutos
• Arquivos grandes podem falhar
• Apenas o proprietário pode baixar
            """
            
            self.bot.edit_message_text(text, chat_id, message_id, reply_markup=keyboard, parse_mode='Markdown')
            
        except Exception as e:
            print(f"Error showing download options: {e}")
            keyboard = types.InlineKeyboardMarkup()
            btn_back = types.InlineKeyboardButton("🔙 Voltar", callback_data=f"{content_type}_play_{stream_id}")
            keyboard.add(btn_back)
            
            self.bot.edit_message_text("❌ Erro ao carregar opções de download", chat_id, message_id, reply_markup=keyboard)
    
    def start_download(self, chat_id, message_id, config, stream_id, content_type, format_index, item_name):
        """Inicia o processo de download"""
        try:
            if not self.is_download_allowed(chat_id):
                self.bot.edit_message_text("❌ Acesso negado!", chat_id, message_id)
                return
            
            # Mostra progresso
            progress_text = f"""
💾 **INICIANDO DOWNLOAD**

🎬 **{item_name}**
📁 **Status:** Preparando download...
⏳ **Progresso:** 0%

**💡 Aguarde, isso pode demorar alguns minutos...**
            """
            
            self.bot.edit_message_text(progress_text, chat_id, message_id, parse_mode='Markdown')
            
            # Inicia download em thread separada
            download_thread = threading.Thread(
                target=self._download_file_thread,
                args=(chat_id, message_id, config, stream_id, content_type, format_index, item_name)
            )
            download_thread.daemon = True
            download_thread.start()
            
        except Exception as e:
            print(f"Error starting download: {e}")
            self.bot.edit_message_text("❌ Erro ao iniciar download", chat_id, message_id)
    
    def _download_file_thread(self, chat_id, message_id, config, stream_id, content_type, format_index, item_name):
        """Thread para fazer o download do arquivo"""
        try:
            # Simula processo de download (aqui você implementaria o download real)
            formats = self.get_file_formats(config, stream_id, content_type)
            selected_format = formats[int(format_index)] if int(format_index) < len(formats) else formats[0]
            
            # URL de download baseada no tipo
            if content_type == 'movie':
                download_url = f"{config['server']}/movie/{config['username']}/{config['password']}/{stream_id}.{selected_format['format']}"
            else:  # episódio de série
                download_url = f"{config['server']}/series/{config['username']}/{config['password']}/{stream_id}.{selected_format['format']}"
            
            # Nome do arquivo
            safe_name = "".join(c for c in item_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
            filename = f"{safe_name}_{stream_id}.{selected_format['format']}"
            filepath = os.path.join(self.download_dir, filename)
            
            # Simula progresso de download
            for progress in [15, 35, 55, 75, 90, 100]:
                time.sleep(2)  # Simula tempo de download
                
                progress_text = f"""
💾 **FAZENDO DOWNLOAD**

🎬 **{item_name}**
📁 **Formato:** {selected_format['quality']} ({selected_format['format'].upper()})
⏳ **Progresso:** {progress}%
{'▓' * (progress // 10)}{'░' * (10 - progress // 10)}

**💡 {'Quase pronto...' if progress > 80 else 'Baixando arquivo...'}**
                """
                
                try:
                    self.bot.edit_message_text(progress_text, chat_id, message_id, parse_mode='Markdown')
                except:
                    pass
            
            # Simula criação do arquivo (em produção, fazer download real aqui)
            with open(filepath, 'w') as f:
                f.write(f"Arquivo simulado: {item_name}\nURL: {download_url}\nFormato: {selected_format}")
            
            # Envia arquivo para o usuário
            success_text = f"""
✅ **DOWNLOAD CONCLUÍDO!**

🎬 **{item_name}**
📁 **Formato:** {selected_format['quality']}
📊 **Tamanho:** {selected_format['size']}

**📤 Enviando arquivo...**
            """
            
            self.bot.edit_message_text(success_text, chat_id, message_id, parse_mode='Markdown')
            
            # Envia o arquivo
            try:
                with open(filepath, 'rb') as f:
                    self.bot.send_document(
                        chat_id,
                        f,
                        caption=f"🎬 **{item_name}**\n📁 Formato: {selected_format['quality']}\n\n**💡 Download concluído com sucesso!**",
                        parse_mode='Markdown'
                    )
                
                # Remove arquivo após envio
                os.remove(filepath)
                
                # Mensagem final
                final_text = f"""
✅ **ARQUIVO ENVIADO!**

🎬 **{item_name}**
📁 **Formato:** {selected_format['quality']}
📤 **Status:** Enviado com sucesso
🗑️ **Arquivo:** Removido do servidor

**💡 Verifique suas mensagens para baixar o arquivo!**
                """
                
                self.bot.edit_message_text(final_text, chat_id, message_id, parse_mode='Markdown')
                
            except Exception as send_error:
                print(f"Error sending file: {send_error}")
                # Remove arquivo mesmo se falhar o envio
                if os.path.exists(filepath):
                    os.remove(filepath)
                
                self.bot.edit_message_text("❌ Erro ao enviar arquivo. Tente novamente.", chat_id, message_id)
            
        except Exception as e:
            print(f"Error in download thread: {e}")
            
            # Remove arquivo se existir
            try:
                if 'filepath' in locals() and os.path.exists(filepath):
                    os.remove(filepath)
            except:
                pass
            
            try:
                self.bot.edit_message_text("❌ Erro durante o download. Tente novamente.", chat_id, message_id)
            except:
                pass
    
    def handle_callback(self, call, config):
        """Manipula callbacks de download"""
        chat_id = call.message.chat.id
        message_id = call.message.message_id
        data = call.data
        
        try:
            if data.startswith("download_options_"):
                # Formato: download_options_movie_12345_Nome do Filme
                parts = data.split("_", 3)
                content_type = parts[2]
                stream_id = parts[3].split("_")[0]
                item_name = "_".join(parts[3].split("_")[1:]) if len(parts[3].split("_")) > 1 else f"{content_type.title()} {stream_id}"
                
                self.show_download_options(chat_id, message_id, config, stream_id, content_type, item_name)
            
            elif data.startswith("download_start_"):
                # Formato: download_start_movie_12345_0
                parts = data.split("_")
                content_type = parts[2]
                stream_id = parts[3]
                format_index = parts[4]
                
                # Obter nome do item (você pode implementar uma função para buscar o nome)
                item_name = f"{content_type.title()} {stream_id}"
                
                self.start_download(chat_id, message_id, config, stream_id, content_type, format_index, item_name)
            
        except Exception as e:
            print(f"Error in download callback: {e}")
            self.bot.answer_callback_query(call.id, "❌ Erro ao processar download")
    
    def cleanup_old_files(self):
        """Remove arquivos antigos do diretório de downloads"""
        try:
            if not os.path.exists(self.download_dir):
                return
            
            current_time = time.time()
            
            for filename in os.listdir(self.download_dir):
                filepath = os.path.join(self.download_dir, filename)
                
                # Remove arquivos com mais de 1 hora
                if os.path.isfile(filepath) and (current_time - os.path.getctime(filepath)) > 3600:
                    os.remove(filepath)
                    print(f"Removed old download file: {filename}")
        
        except Exception as e:
            print(f"Error cleaning up downloads: {e}")
