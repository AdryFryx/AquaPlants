import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../main.dart'; // Para poder volver al Login
import 'configuracion_cultivo.dart';

class PerfilScreen extends StatelessWidget {
  const PerfilScreen({super.key});

  void _cerrarSesion(BuildContext context) async {
    final apiService = ApiService();
    await apiService.logout(); // Borra el JWT de la memoria del teléfono
    
    if (!context.mounted) return;
    
    // Destruye todo el historial de navegación y vuelve al Login
    Navigator.pushAndRemoveUntil(
      context,
      MaterialPageRoute(builder: (context) => const AquaPlantsApp()),
      (route) => false,
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.grey[100],
      appBar: AppBar(
        title: const Text('Mi Perfil', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
        backgroundColor: const Color(0xFF00BFA5),
        elevation: 0,
      ),
      body: Padding(
        padding: const EdgeInsets.all(24.0),
        child: Column(
          children: [
            const CircleAvatar(
              radius: 50,
              backgroundColor: Color(0xFF004D40),
              child: Icon(Icons.person, size: 50, color: Colors.white),
            ),
            const SizedBox(height: 16),
            const Text('Administrador', style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold)),
            const Text('Torre Simulada 1', style: TextStyle(color: Colors.grey)),
            const SizedBox(height: 40),
            ListTile(
              leading: const Icon(Icons.settings, color: Color(0xFF00BFA5)),
              title: const Text('Configurar Umbrales'),
              trailing: const Icon(Icons.arrow_forward_ios, size: 16),
              onTap: () {
                Navigator.push(
                  context,
                  MaterialPageRoute(builder: (context) => const ConfiguracionCultivoScreen()),
                );
              },
            ),
            const Divider(),
            ListTile(
              leading: const Icon(Icons.logout, color: Colors.red),
              title: const Text('Cerrar Sesión', style: TextStyle(color: Colors.red, fontWeight: FontWeight.bold)),
              onTap: () => _cerrarSesion(context),
            ),
          ],
        ),
      ),
    );
  }
}