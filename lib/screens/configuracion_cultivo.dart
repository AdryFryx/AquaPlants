import 'package:flutter/material.dart';
import '../services/api_service.dart';
class ConfiguracionCultivoScreen extends StatefulWidget {
  const ConfiguracionCultivoScreen({super.key});

  @override
  State<ConfiguracionCultivoScreen> createState() => _ConfiguracionCultivoScreenState();
}

class _ConfiguracionCultivoScreenState extends State<ConfiguracionCultivoScreen> {
  // Controladores para los campos de texto
  final _plantaController = TextEditingController(text: 'Lechugas Hidropónicas');
  final _tempMaxController = TextEditingController(text: '25.0');
  final _phIdealController = TextEditingController(text: '6.0');

  bool _isLoading = false;

  void _guardarConfiguracion() async {
    setState(() => _isLoading = true);
    
    final apiService = ApiService();
    final exito = await apiService.guardarConfiguracion(
      _plantaController.text,
      _tempMaxController.text,
    );
    
    if (!mounted) return;
    setState(() => _isLoading = false);
    
    if (exito) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Configuración guardada en Django con éxito'),
          backgroundColor: Colors.green,
        ),
      );
      Navigator.pop(context); // Vuelve al perfil si salió bien
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Error al conectar con el servidor'),
          backgroundColor: Colors.red,
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.grey[100],
      appBar: AppBar(
        title: const Text('Configurar Cultivo', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
        backgroundColor: const Color(0xFF00BFA5),
        iconTheme: const IconThemeData(color: Colors.white), // Flecha de retroceso blanca
        elevation: 0,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Datos del Cultivo', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Color(0xFF004D40))),
            const SizedBox(height: 16),
            TextField(
              controller: _plantaController,
              decoration: InputDecoration(
                labelText: 'Tipo de Planta',
                prefixIcon: const Icon(Icons.grass),
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
              ),
            ),
            const SizedBox(height: 32),
            const Text('Umbrales de Alerta', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Color(0xFF004D40))),
            const SizedBox(height: 16),
            Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _tempMaxController,
                    keyboardType: TextInputType.number,
                    decoration: InputDecoration(
                      labelText: 'Temp. Max (°C)',
                      prefixIcon: const Icon(Icons.thermostat),
                      border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                    ),
                  ),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: TextField(
                    controller: _phIdealController,
                    keyboardType: TextInputType.number,
                    decoration: InputDecoration(
                      labelText: 'pH Ideal',
                      prefixIcon: const Icon(Icons.science),
                      border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 40),
            SizedBox(
              width: double.infinity,
              height: 50,
              child: ElevatedButton(
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF00BFA5),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                ),
                onPressed: _isLoading ? null : _guardarConfiguracion,
                child: _isLoading 
                    ? const CircularProgressIndicator(color: Colors.white)
                    : const Text('Guardar Cambios', style: TextStyle(fontSize: 18, color: Colors.white, fontWeight: FontWeight.bold)),
              ),
            ),
          ],
        ),
      ),
    );
  }
}