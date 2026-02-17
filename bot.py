
import telebot
from telebot import types
import requests
import json
import threading
import time
import os
from datetime import datetime
from backend import backend
from frontend import IPTVFrontend
from canais import CanalManager
from filmes import FilmeManager
from series import SerieManager
from comandos import ComandoManager
from download import DownloadManager

# Token do bot
TOKEN = "8039322971:AAHcDG058maFEh9u-9LqKKBTX6joJzQdY1w"
bot = telebot.TeleBot(TOKEN)

# Dicionário para armazenar dados dos usuários
user_data = {}

class IPTVBot:
    def __init__(self):
        self.frontend = IPTVFrontend(bot)
        self.comando_manager = ComandoManager(bot, backend, self.frontend)
        self.canal_manager = CanalManager(bot, backend, self.frontend)
        self.filme_manager = FilmeManager(bot, backend, self.frontend)
        self.serie_manager = SerieManager(bot, backend, self.frontend)
        self.download_manager = DownloadManager(bot, backend)
        
        # Start cleanup thread
        cleanup_thread = threading.Thread(target=self.cleanup_worker, daemon=True)
        cleanup_thread.start()
    
    def cleanup_worker(self):
        """Worker thread para limpeza automática de arquivos"""
        while True:
            try:
                backend.clean_old_files()
                self.download_manager.cleanup_old_files()
                time.sleep(1800)  # Run every 30 minutes
            except Exception as e:
                print(f"Cleanup error: {e}")
                time.sleep(1800)
    
    def extract_playlist_info(self, url):
        """Extrai informações da playlist IPTV - versão melhorada"""
        try:
            from urllib.parse import urlparse, parse_qs
            
            print(f"Extraindo info da URL: {url}")
            
            # Parse da URL
            parsed = urlparse(url)
            server = f"{parsed.scheme}://{parsed.netloc}"
            
            # Extrai parâmetros da query string
            query_params = parse_qs(parsed.query)
            
            username = None
            password = None
            
            # Tenta extrair username e password dos parâmetros
            if 'username' in query_params:
                username = query_params['username'][0]
            if 'password' in query_params:
                password = query_params['password'][0]
            
            print(f"Server: {server}, Username: {username}, Password: {password}")
            
            if username and password:
                config = {
                    'server': server,
                    'username': username,
                    'password': password,
                    'api_url': f"{server}/player_api.php"
                }
                print(f"Configuração extraída: {config}")
                return config
            
            return None
            
        except Exception as e:
            print(f"Erro ao extrair info da playlist: {e}")
            return None
    
    def test_connection(self, config):
        """Testa a conexão com o servidor IPTV - versão melhorada"""
        try:
            print(f"Testando conexão com: {config['api_url']}")
            
            # Parâmetros para testar a conexão
            params = {
                'username': config['username'],
                'password': config['password'],
                'action': 'get_account_info'
            }
            
            print(f"Parâmetros: {params}")
            
            # Faz a requisição
            response = requests.get(config['api_url'], params=params, timeout=10)
            print(f"Status code: {response.status_code}")
            print(f"Response: {response.text[:200]}...")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"JSON data: {data}")
                    
                    # Verifica se há erro na resposta
                    if isinstance(data, dict) and 'user_info' in data:
                        print("Conexão bem-sucedida!")
                        return True
                    elif isinstance(data, dict) and not data.get('error'):
                        print("Conexão bem-sucedida (dados válidos)!")
                        return True
                    else:
                        print(f"Erro na resposta: {data}")
                        return False
                        
                except json.JSONDecodeError:
                    # Se não for JSON, mas status 200, assume que a conexão está OK
                    print("Resposta não é JSON, mas status 200 - assumindo conexão OK")
                    return True
            else:
                print(f"Erro HTTP: {response.status_code}")
                return False
                
        except requests.exceptions.Timeout:
            print("Timeout na conexão")
            return False
        except requests.exceptions.ConnectionError:
            print("Erro de conexão")
            return False
        except Exception as e:
            print(f"Erro no teste de conexão: {e}")
            return False
    
    def safe_send_message(self, chat_id, text, reply_markup=None, parse_mode=None):
        """Envia mensagem de forma segura"""
        try:
            return bot.send_message(chat_id, text, reply_markup=reply_markup, parse_mode=parse_mode)
        except Exception as e:
            print(f"Error sending message: {e}")
            return None
    
    def safe_edit_message(self, chat_id, message_id, text, reply_markup=None, parse_mode=None):
        """Edita mensagem de forma segura"""
        try:
            bot.edit_message_text(text, chat_id, message_id, reply_markup=reply_markup, parse_mode=parse_mode)
        except Exception as e:
            print(f"Error editing message: {e}")
            # Se falhar ao editar, tenta deletar e enviar nova
            try:
                bot.delete_message(chat_id, message_id)
                self.safe_send_message(chat_id, text, reply_markup, parse_mode)
            except:
                pass

# Instância do bot IPTV
iptv_bot = IPTVBot()

@bot.message_handler(commands=['start'])
def start_message(message):
    """Mensagem de boas-vindas"""
    welcome_text = """
🎬 **Bem-vindo ao IPTV Bot Profissional v3.0!** 📺

🚀 **O bot mais avançado para IPTV no Telegram!**

**✨ Recursos únicos:**
• 🛡️ Sistema anti-spam profissional
• 📄 Geração de arquivos M3U personalizados com categorias
• ⭐ Sistema de seleções individual e por categoria completa
• 📊 Informações detalhadas do servidor
• 🔄 Cache inteligente para performance
• 📱 Interface com paginação completa
• 💾 Download de filmes e episódios (apenas dono)
• 📤 Envio para grupos (apenas dono)
• 🏷️ Renomeação de categorias personalizadas

**🎯 Como usar:**
1️⃣ Envie a URL da sua playlist IPTV
2️⃣ Navegue pelos conteúdos com paginação
3️⃣ Selecione itens individuais ou categorias completas
4️⃣ Renomeie categorias conforme desejar
5️⃣ Gere arquivos M3U personalizados

**📝 Formato da URL:**
`http://servidor.com/get.php?username=user&password=pass`

**🔥 Pronto para uma experiência incrível?**
Envie sua URL de playlist para começar!
    """
    
    iptv_bot.safe_send_message(message.chat.id, welcome_text, parse_mode='Markdown')

@bot.message_handler(func=lambda message: True and not message.text.startswith('/'))
def handle_message(message):
    """Processa mensagens de texto"""
    chat_id = message.chat.id
    text = message.text.strip()
    
    # Verifica se é contexto de compartilhamento
    if chat_id in backend.user_context:
        context = backend.user_context[chat_id]
        if context.get('action') == 'share':
            iptv_bot.comando_manager.process_group_share(message, context)
            del backend.user_context[chat_id]
            return
        elif context.get('action') == 'rename_category':
            # Processa renomeação de categoria
            category_name = text.strip()
            if category_name:
                category_type = context['category_type']
                category_id = context['category_id']
                config = context['config']
                
                # Adiciona categoria completa com nome personalizado
                added_count = backend.add_full_category(
                    chat_id, config, category_type, category_id, category_name
                )
                
                if added_count > 0:
                    iptv_bot.safe_send_message(
                        chat_id,
                        f"""✅ **Categoria adicionada com sucesso!**

🏷️ **Nome:** {category_name}
📊 **Tipo:** {category_type.title()}
📝 **Itens adicionados:** {added_count}

**🎉 Categoria completa salva para o arquivo M3U!**""",
                        parse_mode='Markdown'
                    )
                else:
                    iptv_bot.safe_send_message(
                        chat_id,
                        "❌ **Erro ao adicionar categoria**\n\nNenhum item foi encontrado nesta categoria.",
                        parse_mode='Markdown'
                    )
            else:
                iptv_bot.safe_send_message(
                    chat_id,
                    "❌ **Nome inválido**\n\nPor favor, envie um nome válido para a categoria.",
                    parse_mode='Markdown'
                )
            
            del backend.user_context[chat_id]
            return
    
    # Rate limiting check (exceto para o dono)
    if not backend.check_rate_limit(chat_id):
        iptv_bot.frontend.show_rate_limit_error(chat_id)
        return
    
    # Verifica se é uma URL válida
    if not text.startswith('http'):
        iptv_bot.safe_send_message(chat_id, """
❌ **URL inválida!**

Por favor, envie uma URL válida no formato:
`http://servidor.com/get.php?username=user&password=pass`

**Exemplo correto:**
`http://exemplo.com/get.php?username=meuuser&password=minhasenha`
        """, parse_mode='Markdown')
        return
    
    # Mostra mensagem de carregamento
    loading_msg = iptv_bot.safe_send_message(
        chat_id, "⏳ **Analisando playlist...**\n\n🔍 Verificando servidor\n📡 Testando conexão\n⚡ Validando credenciais", 
        parse_mode='Markdown'
    )
    
    try:
        # Extrai informações da playlist
        config = iptv_bot.extract_playlist_info(text)
        
        if not config:
            if loading_msg:
                iptv_bot.safe_edit_message(
                    chat_id, loading_msg.message_id,
                    """❌ **URL inválida!** 

A URL deve conter `username` e `password`.

**Formato correto:**
`http://servidor.com/get.php?username=USER&password=PASS`""",
                    parse_mode='Markdown'
                )
            return
        
        # Testa conexão
        if not iptv_bot.test_connection(config):
            if loading_msg:
                iptv_bot.safe_edit_message(
                    chat_id, loading_msg.message_id,
                    """❌ **Falha na conexão!**

Não foi possível conectar com o servidor.

**Dados da conexão:**
🌐 **Servidor:** {server}
👤 **Usuário:** {username}
🔗 **API:** {api_url}

**Possíveis causas:**
• Servidor offline ou sobrecarregado
• Credenciais incorretas ou expiradas
• Problema de rede temporário
• Servidor bloqueando requisições

**💡 Sugestões:**
• Verifique se as credenciais estão corretas
• Tente novamente em alguns minutos
• Contate o provedor do serviço IPTV""".format(
                        server=config.get('server', 'N/A'),
                        username=config.get('username', 'N/A'),
                        api_url=config.get('api_url', 'N/A')
                    ),
                    parse_mode='Markdown'
                )
            return
        
        # Salva configuração do usuário
        user_data[chat_id] = config
        
        # Remove mensagem de carregamento
        if loading_msg:
            try:
                bot.delete_message(chat_id, loading_msg.message_id)
            except:
                pass
        
        # Mensagem de sucesso
        success_msg = iptv_bot.safe_send_message(chat_id, """
✅ **Conexão estabelecida com sucesso!**

🎉 Playlist configurada e validada
🚀 Sistema pronto para uso
⚡ Cache otimizado ativado

**Preparando menu principal...**
        """, parse_mode='Markdown')
        
        time.sleep(1.5)
        if success_msg:
            try:
                bot.delete_message(chat_id, success_msg.message_id)
            except:
                pass
        
        iptv_bot.frontend.show_main_menu(chat_id)
        
    except Exception as e:
        print(f"Error handling playlist URL: {e}")
        if loading_msg:
            try:
                iptv_bot.safe_edit_message(
                    chat_id, loading_msg.message_id,
                    "❌ **Erro interno**\n\nTente novamente em alguns segundos."
                )
            except:
                pass

# ... keep existing code (callback_handler function and other handlers) ...

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    """Manipula todos os callbacks dos botões"""
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    data = call.data
    
    try:
        # Rate limiting check (exceto para o dono)
        if not backend.check_rate_limit(chat_id):
            bot.answer_callback_query(call.id, "⚠️ Muitas solicitações! Aguarde alguns segundos.", show_alert=True)
            return
        
        # Handle different callback types
        if data == "nova_playlist":
            try:
                iptv_bot.safe_edit_message(
                    chat_id, message_id,
                    """🔄 **Nova Playlist**

📝 Envie a nova URL da playlist IPTV:

**Formato:**
`http://servidor.com/get.php?username=USER&password=PASS`

**💡 Dica:** Cole a URL completa com username e password.""",
                    parse_mode='Markdown'
                )
            except Exception as e:
                print(f"Error nova_playlist: {e}")
        
        elif data == "menu_principal":
            iptv_bot.frontend.show_main_menu(chat_id, message_id)
        
        elif data == "server_info":
            if chat_id not in user_data:
                bot.answer_callback_query(call.id, "❌ Configure uma playlist primeiro!")
                return
            
            server_info = backend.get_server_info(user_data[chat_id])
            iptv_bot.frontend.show_server_info(chat_id, message_id, server_info)
        
        elif data == "menu_selections":
            selections = backend.get_user_selections(chat_id)
            iptv_bot.frontend.show_selections_menu(chat_id, message_id, selections)
        
        elif data == "generate_m3u":
            if chat_id not in user_data:
                bot.answer_callback_query(call.id, "❌ Configure uma playlist primeiro!")
                return
            
            try:
                # Verifica se há seleções
                selections = backend.get_user_selections(chat_id)
                total_items = len(selections.get('channels', [])) + len(selections.get('movies', [])) + len(selections.get('series', []))
                
                if total_items == 0:
                    bot.answer_callback_query(call.id, "❌ Nenhum item selecionado! Adicione conteúdos primeiro.", show_alert=True)
                    return
                
                filename = backend.generate_m3u_file(chat_id, user_data[chat_id])
                
                if filename:
                    with open(filename, 'rb') as f:
                        bot.send_document(
                            chat_id,
                            f,
                            caption=f"""📄 **Arquivo M3U Personalizado Gerado!**

✅ **Conteúdo incluído:**
• 📺 Canais: {len(selections.get('channels', []))}
• 🎬 Filmes: {len(selections.get('movies', []))}
• 📺 Séries: {len(selections.get('series', []))}
• 📊 **Total: {total_items} itens**

🏷️ **Categorias personalizadas mantidas**
🎯 **Pronto para usar em qualquer player IPTV**
⚡ **Otimizado para máxima compatibilidade**

**💡 Como usar:**
1. Baixe o arquivo M3U
2. Importe no seu player IPTV favorito
3. Desfrute do conteúdo selecionado!""",
                            parse_mode='Markdown'
                        )
                    
                    # Remove arquivo após envio
                    try:
                        os.remove(filename)
                    except:
                        pass
                    
                    bot.answer_callback_query(call.id, "✅ Arquivo M3U enviado com sucesso!")
                else:
                    bot.answer_callback_query(call.id, "❌ Erro ao gerar arquivo M3U")
                
            except Exception as e:
                print(f"Error generating M3U: {e}")
                bot.answer_callback_query(call.id, "❌ Erro ao gerar arquivo M3U")
        
        elif data == "clear_selections":
            if chat_id in backend.user_selections:
                backend.user_selections[chat_id] = {'channels': [], 'movies': [], 'series': []}
            
            bot.answer_callback_query(call.id, "🗑️ Todas as seleções foram removidas!")
            
            selections = backend.get_user_selections(chat_id)
            iptv_bot.frontend.show_selections_menu(chat_id, message_id, selections)
        
        elif data == "menu_canais":
            if chat_id not in user_data:
                bot.answer_callback_query(call.id, "❌ Configure uma playlist primeiro!")
                return
            iptv_bot.canal_manager.show_categories(chat_id, message_id, user_data[chat_id])
        
        elif data == "menu_filmes":
            if chat_id not in user_data:
                bot.answer_callback_query(call.id, "❌ Configure uma playlist primeiro!")
                return
            iptv_bot.filme_manager.show_categories(chat_id, message_id, user_data[chat_id])
        
        elif data == "menu_series":
            if chat_id not in user_data:
                bot.answer_callback_query(call.id, "❌ Configure uma playlist primeira!")
                return
            iptv_bot.serie_manager.show_categories(chat_id, message_id, user_data[chat_id])
        
        # Callbacks de download
        elif data.startswith("download_"):
            iptv_bot.download_manager.handle_callback(call, user_data.get(chat_id))
        
        # Comandos especiais do dono
        elif data == "admin_panel" and backend.is_owner(chat_id):
            keyboard = iptv_bot.comando_manager.create_admin_keyboard()
            iptv_bot.safe_edit_message(
                chat_id, message_id,
                f"""
👑 **PAINEL ADMINISTRATIVO**

**📊 Estatísticas:**
• Requisições: {backend.stats['total_requests']}
• Cache hits: {backend.stats['cache_hits']}
• Downloads: {backend.stats.get('downloads', 0)}
• Usuários ativos: {len(backend.stats.get('users', []))}

**🛠️ Controles disponíveis:**
• 📊 Estatísticas detalhadas
• 🗄️ Limpeza de cache
• 💾 Gerenciamento de downloads
                """,
                keyboard, 'Markdown'
            )
        
        elif data.startswith("admin_") and backend.is_owner(chat_id):
            if data == "admin_stats":
                stats = backend.get_stats()
                iptv_bot.safe_edit_message(
                    chat_id, message_id,
                    f"""
📊 **ESTATÍSTICAS DETALHADAS**

**📈 Uso do sistema:**
• Total de requisições: {stats['total_requests']}
• Cache hits: {stats['cache_hits']}
• Tamanho do cache: {stats['cache_size']} itens
• Downloads realizados: {stats.get('downloads', 0)}

**👥 Usuários:**
• Usuários ativos: {stats['active_users']}
• Seleções salvas: {stats['selections']}

**⚡ Sistema:**
• Uptime: {int(time.time() - stats['uptime'])}s
• Memória cache: {stats['cache_size'] * 50}KB (aprox.)
                    """,
                    iptv_bot.comando_manager.create_admin_keyboard(),
                    'Markdown'
                )
            elif data == "admin_clear_cache":
                cleared = backend.clear_cache()
                bot.answer_callback_query(call.id, f"🗄️ Cache limpo! {cleared} itens removidos.")
        
        # Downloads e compartilhamento (apenas dono)
        elif data.startswith(("canal_download_", "filme_download_", "serie_download_", "episode_download_")):
            if not backend.is_owner(chat_id):
                bot.answer_callback_query(call.id, "❌ Apenas o dono pode fazer downloads!", show_alert=True)
                return
            
            parts = data.split("_")
            item_type = parts[0]
            item_id = parts[2]
            iptv_bot.comando_manager.handle_download_request(call, item_type, item_id, user_data.get(chat_id))
        
        elif data.startswith(("canal_share_", "filme_share_", "serie_share_")):
            if not backend.is_owner(chat_id):
                bot.answer_callback_query(call.id, "❌ Apenas o dono pode enviar para grupos!", show_alert=True)
                return
            
            parts = data.split("_")
            item_type = parts[0]
            item_id = parts[2]
            iptv_bot.comando_manager.handle_share_request(call, item_type, item_id, user_data.get(chat_id))
        
        # Callbacks para adicionar categoria completa
        elif data.startswith("add_full_category_"):
            if chat_id not in user_data:
                bot.answer_callback_query(call.id, "❌ Configure uma playlist primeiro!")
                return
            
            parts = data.split("_")
            if len(parts) >= 4:
                category_type = parts[3]  # channels, movies, series
                category_id = parts[4] if len(parts) > 4 else parts[3]
                
                # Solicita nome personalizado para a categoria
                bot.answer_callback_query(call.id, "📝 Envie o nome personalizado para esta categoria")
                
                msg = iptv_bot.safe_send_message(
                    chat_id,
                    f"""
🏷️ **Renomear Categoria Completa**

**📁 Tipo:** {category_type.title()}
**🆔 ID:** {category_id}

**💡 Envie o nome que deseja usar para esta categoria no M3U:**

**Exemplos:**
• "Meus Canais de Esporte"
• "Filmes de Ação Favoritos"
• "Séries Netflix Premium"

📝 **Digite o nome personalizado:**
                    """,
                    parse_mode='Markdown'
                )
                
                # Context para próxima mensagem
                if not hasattr(backend, 'user_context'):
                    backend.user_context = {}
                backend.user_context[chat_id] = {
                    'action': 'rename_category',
                    'category_type': category_type,
                    'category_id': category_id,
                    'config': user_data[chat_id]
                }
        
        # Delegação para managers específicos
        elif data.startswith("canal_"):
            iptv_bot.canal_manager.handle_callback(call, user_data.get(chat_id))
        
        elif data.startswith("filme_"):
            iptv_bot.filme_manager.handle_callback(call, user_data.get(chat_id))
        
        elif data.startswith("serie_"):
            iptv_bot.serie_manager.handle_callback(call, user_data.get(chat_id))
        
        elif data in ["page_info", "empty"]:
            bot.answer_callback_query(call.id, "ℹ️ Informação de página" if data == "page_info" else "")
        
        else:
            bot.answer_callback_query(call.id, "⚠️ Ação não reconhecida")
        
        # Always answer callback to remove loading state
        try:
            bot.answer_callback_query(call.id)
        except:
            pass
        
    except Exception as e:
        print(f"Callback error: {e}")
        try:
            bot.answer_callback_query(call.id, "❌ Erro interno. Tente novamente.")
        except:
            pass

@bot.message_handler(commands=['admin'])
def admin_command(message):
    """Comando especial para o dono"""
    if backend.is_owner(message.from_user.id):
        keyboard = iptv_bot.comando_manager.create_admin_keyboard()
        iptv_bot.safe_send_message(
            message.chat.id,
            """
👑 **PAINEL ADMINISTRATIVO**

Bem-vindo, Edivaldo Silva!

**🎛️ Controles especiais disponíveis:**
• 📊 Estatísticas completas do sistema
• 👥 Gerenciamento de usuários
• 🗄️ Controle de cache
• 💾 Sistema de downloads
• 📋 Visualização de logs

**🔓 Permissões especiais ativas:**
• ✅ Downloads ilimitados de filmes e séries
• ✅ Envio para grupos
• ✅ Sem rate limiting
• ✅ Acesso total ao sistema
            """,
            keyboard, 'Markdown'
        )
    else:
        iptv_bot.safe_send_message(message.chat.id, "❌ Comando disponível apenas para o administrador.")

@bot.message_handler(commands=['stats'])
def show_stats(message):
    """Mostra estatísticas básicas"""
    stats = backend.get_stats()
    stats_text = f"""
📊 **Estatísticas do Bot**

👥 Usuários ativos: {stats['active_users']}
💾 Items no cache: {stats['cache_size']}
⭐ Seleções salvas: {stats['selections']}
🔄 Total de requisições: {stats['total_requests']}
💾 Downloads realizados: {stats.get('downloads', 0)}
⏱️ Uptime: {int(time.time() - stats['uptime'])}s

**🚀 Bot IPTV Profissional v3.0**
    """
    iptv_bot.safe_send_message(message.chat.id, stats_text, parse_mode='Markdown')

if __name__ == "__main__":
    start_time = time.time()
    print("🚀 Bot IPTV Profissional v3.0 iniciado!")
    print("📡 Sistema anti-spam ativado")
    print("💾 Cache inteligente configurado") 
    print("🧹 Limpeza automática de arquivos ativa")
    print("👑 Privilégios especiais para o dono configurados")
    print("🏷️ Sistema de categorias personalizáveis ativo")
    print("📱 Paginação completa implementada")
    print("💾 Sistema de downloads para filmes e séries ativo")
    print("⚡ Aceita múltiplos formatos de URL IPTV")
    print("🛡️ Sistema robusto de tratamento de erros ativo")
    print("Pressione Ctrl+C para parar")
    
    try:
        bot.infinity_polling(none_stop=True, timeout=60)
    except KeyboardInterrupt:
        print("\n👋 Bot finalizado com segurança!")
        print("🧹 Limpeza final executada")
        backend.clean_old_files()
