
import requests
import json
import os
import time
from typing import Dict, List, Optional, Any

class Backend:
    def __init__(self):
        self.cache = {}
        self.cache_time = 3600  # Tempo de vida do cache em segundos
        self.owner_id = 1985282432  # ID do Edivaldo Silva
        self.user_selections = {}  # Armazena seleções dos usuários
        self.stats = {
            'total_requests': 0,
            'cache_hits': 0,
            'active_users': 0,
            'selections': 0,
            'uptime': time.time()
        }
        self.rate_limits = {}  # Controle de taxa de requisições
        self.rate_limit_time = 60  # Tempo para resetar o limite (segundos)
        self.rate_limit_max = 20  # Máximo de requisições permitidas
        self.user_context = {}  # Armazena contexto por usuário (ex: dados de formulário)
    
    def is_owner(self, user_id: int) -> bool:
        """Verifica se é o dono do bot"""
        return user_id == self.owner_id
    
    def check_rate_limit(self, user_id: int) -> bool:
        """Verifica e aplica rate limiting"""
        now = time.time()
        
        # Dono não tem rate limit
        if self.is_owner(user_id):
            return True
        
        if user_id not in self.rate_limits:
            self.rate_limits[user_id] = {'count': 0, 'last_request': now}
        
        user_limit = self.rate_limits[user_id]
        
        # Reseta contagem se o tempo expirou
        if now - user_limit['last_request'] > self.rate_limit_time:
            user_limit['count'] = 0
        
        # Incrementa contagem
        user_limit['count'] += 1
        user_limit['last_request'] = now
        
        # Verifica se excedeu o limite
        if user_limit['count'] > self.rate_limit_max:
            return False
        
        return True
    
    def get_stats(self) -> Dict:
        """Retorna estatísticas do sistema"""
        self.stats['cache_size'] = len(self.cache)
        self.stats['active_users'] = len(self.user_selections)
        self.stats['selections'] = sum(len(v['channels']) + len(v['movies']) + len(v['series']) for v in self.user_selections.values())
        return self.stats
    
    def clear_cache(self) -> int:
        """Limpa o cache e retorna o número de itens removidos"""
        removed = len(self.cache)
        self.cache = {}
        return removed
    
    def make_api_request(self, config: Dict, params: Dict) -> Optional[Dict]:
        """Faz requisição para a API do servidor - versão melhorada"""
        self.stats['total_requests'] += 1
        
        cache_key = hash(json.dumps(params, sort_keys=True))
        
        # Verifica se está em cache
        if cache_key in self.cache and (time.time() - self.cache[cache_key]['time']) < self.cache_time:
            self.stats['cache_hits'] += 1
            return self.cache[cache_key]['data']
        
        try:
            print(f"Fazendo requisição para: {config['api_url']}")
            print(f"Parâmetros: {params}")
            
            # Tenta primeiro com GET
            response = requests.get(config['api_url'], params=params, timeout=15)
            print(f"Response status: {response.status_code}")
            print(f"Response content: {response.text[:300]}...")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"JSON parsed successfully: {type(data)}")
                    
                    # Armazena em cache
                    self.cache[cache_key] = {'time': time.time(), 'data': data}
                    return data
                    
                except json.JSONDecodeError as e:
                    print(f"JSON decode error: {e}")
                    # Se não for JSON válido, tenta interpretar como resposta válida
                    if response.text.strip():
                        print("Resposta não é JSON, mas contém dados")
                        return {'status': 'ok', 'raw_data': response.text}
                    return None
            else:
                print(f"HTTP Error: {response.status_code}")
                # Tenta com POST se GET falhou
                print("Tentando com POST...")
                response = requests.post(config['api_url'], data=params, timeout=15)
                print(f"POST Response status: {response.status_code}")
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        self.cache[cache_key] = {'time': time.time(), 'data': data}
                        return data
                    except json.JSONDecodeError:
                        return {'status': 'ok', 'raw_data': response.text}
                
                return None
            
        except requests.exceptions.Timeout:
            print("Request timeout")
            return None
        except requests.exceptions.ConnectionError as e:
            print(f"Connection error: {e}")
            return None
        except Exception as e:
            print(f"General API error: {e}")
            return None
    
    def get_server_info(self, config: Dict) -> Optional[Dict]:
        """Obtém informações do servidor"""
        try:
            params = {
                'username': config['username'],
                'password': config['password'],
                'action': 'get_account_info'
            }
            
            data = self.make_api_request(config, params)
            
            if data:
                # Tenta extrair informações da resposta
                user_info = data.get('user_info', {}) if isinstance(data, dict) else {}
                server_info = data.get('server_info', {}) if isinstance(data, dict) else {}
                
                return {
                    'server': config['server'],
                    'username': config['username'],
                    'status': user_info.get('status', 'Active') if user_info else 'Online',
                    'exp_date': user_info.get('exp_date', 'N/A') if user_info else 'N/A',
                    'available_channels': server_info.get('available_channels', '0') if server_info else '0',
                    'available_movies': server_info.get('available_movies', '0') if server_info else '0',
                    'available_series': server_info.get('available_series', '0') if server_info else '0',
                    'raw_response': str(data)[:200]  # Para debug
                }
            
            return {
                'server': config['server'],
                'username': config['username'],
                'status': 'Connected',
                'exp_date': 'N/A',
                'available_channels': 'N/A',
                'available_movies': 'N/A',
                'available_series': 'N/A'
            }
            
        except Exception as e:
            print(f"Error getting server info: {e}")
            return None

    # ... keep existing code (add_full_category, get_user_selections, etc.) ...

    def add_full_category(self, user_id, config, category_type, category_id, custom_name):
        """Adiciona uma categoria completa ao M3U"""
        try:
            added_count = 0
            
            if category_type == 'channels':
                # Obtém todos os canais da categoria
                params = {
                    'username': config['username'],
                    'password': config['password'],
                    'action': 'get_live_streams',
                    'category_id': category_id
                }
                
                response = self.make_api_request(config, params)
                items = response if isinstance(response, list) else []
                
                for item in items:
                    channel_data = {
                        'id': item.get('stream_id', item.get('id')),
                        'name': item.get('name', 'Canal sem nome'),
                        'logo': item.get('stream_icon', ''),
                        'container': item.get('container_extension', 'ts'),
                        'category': custom_name  # Usa nome personalizado
                    }
                    
                    if self.add_to_selection(user_id, 'channels', channel_data):
                        added_count += 1
            
            elif category_type == 'movies':
                # Obtém todos os filmes da categoria
                params = {
                    'username': config['username'],
                    'password': config['password'],
                    'action': 'get_vod_streams',
                    'category_id': category_id
                }
                
                response = self.make_api_request(config, params)
                items = response if isinstance(response, list) else []
                
                for item in items:
                    movie_data = {
                        'id': item.get('stream_id', item.get('id')),
                        'name': item.get('name', 'Filme sem nome'),
                        'logo': item.get('stream_icon', ''),
                        'container': item.get('container_extension', 'mp4'),
                        'category': custom_name  # Usa nome personalizado
                    }
                    
                    if self.add_to_selection(user_id, 'movies', movie_data):
                        added_count += 1
            
            elif category_type == 'series':
                # Obtém todas as séries da categoria
                params = {
                    'username': config['username'],
                    'password': config['password'],
                    'action': 'get_series',
                    'category_id': category_id
                }
                
                response = self.make_api_request(config, params)
                items = response if isinstance(response, list) else []
                
                for item in items:
                    # Para cada série, obtém todos os episódios
                    series_params = {
                        'username': config['username'],
                        'password': config['password'],
                        'action': 'get_series_info',
                        'series_id': item.get('series_id', item.get('id'))
                    }
                    
                    series_info = self.make_api_request(config, series_params)
                    
                    if series_info and isinstance(series_info, dict) and 'episodes' in series_info:
                        for season_num, episodes in series_info['episodes'].items():
                            for episode in episodes:
                                episode_data = {
                                    'id': episode.get('id'),
                                    'name': f"{item.get('name', 'Série')} - S{season_num}E{episode.get('episode_num', '?')} - {episode.get('title', 'Episódio')}",
                                    'logo': item.get('cover', ''),
                                    'container': episode.get('container_extension', 'mp4'),
                                    'category': custom_name,  # Usa nome personalizado
                                    'series_name': item.get('name', 'Série'),
                                    'season': season_num,
                                    'episode': episode.get('episode_num', '?')
                                }
                                
                                if self.add_to_selection(user_id, 'series', episode_data):
                                    added_count += 1
            
            return added_count
            
        except Exception as e:
            print(f"Error adding full category: {e}")
            return 0
    
    def get_user_selections(self, user_id: int) -> Dict:
        """Retorna as seleções do usuário"""
        if user_id not in self.user_selections:
            self.user_selections[user_id] = {'channels': [], 'movies': [], 'series': []}
        return self.user_selections[user_id]
    
    def get_selection_stats(self, user_id: int) -> Dict:
        """Retorna estatísticas das seleções do usuário"""
        selections = self.get_user_selections(user_id)
        
        # Calcula número de episódios
        episode_count = 0
        for serie in selections['series']:
            try:
                episode_count += 1
            except:
                pass
        
        total_items = len(selections['channels']) + len(selections['movies']) + len(selections['series'])
        
        return {
            'channels': len(selections['channels']),
            'movies': len(selections['movies']),
            'series': len(selections['series']),
            'episodes': episode_count,
            'total_items': total_items
        }
    
    def add_to_selection(self, user_id: int, item_type: str, item_data: Dict) -> bool:
        """Adiciona um item à seleção do usuário"""
        selections = self.get_user_selections(user_id)
        
        item_id = item_data.get('id')
        
        if not item_id:
            print("Item ID not found in item_data:", item_data)
            return False
        
        # Verifica se o item já existe na seleção
        if any(item['id'] == item_id for item in selections[item_type]):
            return False
        
        # Adiciona o item
        selections[item_type].append(item_data)
        return True
    
    def clear_user_selections(self, user_id: int, item_type: str = None):
        """Limpa as seleções do usuário"""
        if user_id in self.user_selections:
            if item_type:
                self.user_selections[user_id][item_type] = []
            else:
                self.user_selections[user_id] = {'channels': [], 'movies': [], 'series': []}
    
    def generate_m3u_file(self, user_id: int, config: Dict) -> Optional[str]:
        """Gera o arquivo M3U com as seleções do usuário"""
        try:
            selections = self.get_user_selections(user_id)
            
            if not selections or all(not v for v in selections.values()):
                return None
            
            filename = f"playlist_{user_id}.m3u"
            filepath = os.path.join(os.getcwd(), filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write("#EXTM3U\n")
                
                # Adiciona canais
                for channel in selections['channels']:
                    channel_url = f"{config['server']}/live/{config['username']}/{config['password']}/{channel['id']}.{channel['container']}"
                    f.write(f"#EXTINF:-1 tvg-id=\"{channel['id']}\" tvg-name=\"{channel['name']}\" tvg-logo=\"{channel['logo']}\" group-title=\"{channel['category']}\",{channel['name']}\n")
                    f.write(f"{channel_url}\n")
                
                # Adiciona filmes
                for movie in selections['movies']:
                    movie_url = f"{config['server']}/movie/{config['username']}/{config['password']}/{movie['id']}.{movie['container']}"
                    f.write(f"#EXTINF:-1 tvg-id=\"{movie['id']}\" tvg-name=\"{movie['name']}\" tvg-logo=\"{movie['logo']}\" group-title=\"{movie['category']}\",{movie['name']}\n")
                    f.write(f"{movie_url}\n")
                
                # Adiciona séries (episódios)
                for serie in selections['series']:
                    serie_url = f"{config['server']}/series/{config['username']}/{config['password']}/{serie['id']}.{serie['container']}"
                    f.write(f"#EXTINF:-1 tvg-id=\"{serie['id']}\" tvg-name=\"{serie['name']}\" tvg-logo=\"{serie['logo']}\" group-title=\"{serie['category']}\",{serie['name']}\n")
                    f.write(f"{serie_url}\n")
            
            return filepath
            
        except Exception as e:
            print(f"Error generating M3U file: {e}")
            return None
    
    def clean_old_files(self):
        """Limpa arquivos M3U antigos"""
        try:
            now = time.time()
            cutoff = now - (24 * 3600)  # Remove arquivos com mais de 24 horas
            
            for filename in os.listdir():
                if filename.startswith("playlist_") and filename.endswith(".m3u"):
                    filepath = os.path.join(os.getcwd(), filename)
                    
                    # Verifica se o arquivo foi modificado antes do cutoff
                    if os.path.getmtime(filepath) < cutoff:
                        os.remove(filepath)
                        print(f"Arquivo M3U antigo removido: {filename}")
        
        except Exception as e:
            print(f"Erro ao limpar arquivos antigos: {e}")

backend = Backend()
