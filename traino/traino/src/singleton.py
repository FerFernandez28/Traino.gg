class SystemConfigSingleton:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            # Si no existe la instancia en memoria, la creamos x unica vez
            cls._instance = super(SystemConfigSingleton, cls).__new__(cls)
            
            # Seteamo las variables globales de la plataforma de 9z
            cls._instance.platform_name = "Traino.gg"
            cls._instance.region = "South America"
            cls._instance.game_target = "Rainbow Six Siege"
            cls._instance.version = "1.0.0-PRO"
            print("Instancia única de Configuración creada con éxito.[SINGLETON]")
        else:
            print("Reutilizando la instancia existente en memoria. [SINGLETON] ")
        
        return cls._instance