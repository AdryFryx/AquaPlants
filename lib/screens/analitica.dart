import 'package:flutter/material.dart';
import 'package:aquaplants/services/api_service.dart';

class AnaliticaScreen extends StatefulWidget {
  const AnaliticaScreen({super.key});

  @override
  State<AnaliticaScreen> createState() => _AnaliticaScreenState();
}

class _AnaliticaScreenState extends State<AnaliticaScreen> {
  int _diasSeleccionados = 7; // Por defecto 1 semana
  String _tituloPeriodo = 'Resumen Semanal';

  // Función para abrir el menú de selección de fechas
  void _mostrarFiltroFechas() {
    showModalBottomSheet(
      context: context,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (context) {
        return SafeArea(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Padding(
                padding: EdgeInsets.all(16.0),
                child: Text('Filtrar Histórico', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
              ),
              ListTile(
                leading: const Icon(Icons.history_toggle_off),
                title: const Text('Últimos 3 días'),
                onTap: () => _aplicarFiltro(3, 'Resumen: Últimos 3 días'),
              ),
              ListTile(
                leading: const Icon(Icons.calendar_view_week),
                title: const Text('Última semana'),
                onTap: () => _aplicarFiltro(7, 'Resumen Semanal'),
              ),
              ListTile(
                leading: const Icon(Icons.calendar_month),
                title: const Text('Último mes'),
                onTap: () => _aplicarFiltro(30, 'Resumen Mensual'),
              ),
            ],
          ),
        );
      },
    );
  }

  void _aplicarFiltro(int dias, String titulo) {
    setState(() {
      _diasSeleccionados = dias;
      _tituloPeriodo = titulo;
    });
    Navigator.pop(context); // Cierra el modal
    
    
    ApiService().getMediciones(dias: _diasSeleccionados).then((datos) {
    setState(() {});
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.grey[100],
      appBar: AppBar(
        title: const Text('Análisis Agronómico', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
        backgroundColor: const Color(0xFF1976D2),
        elevation: 0,
        actions: [
          IconButton(
            icon: const Icon(Icons.calendar_month, color: Colors.white),
            onPressed: _mostrarFiltroFechas, // Conectamos el botón al modal
          )
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // El texto ahora cambia dinámicamente según el filtro
            Text(_tituloPeriodo, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Color(0xFF004D40))),
            const SizedBox(height: 16),
            Row(
              children: [
                Expanded(child: _buildStatCard('Temp. Promedio', '23.4°C', Icons.thermostat, Colors.orange)),
                const SizedBox(width: 12),
                Expanded(child: _buildStatCard('Consumo Agua', '45 L', Icons.water_drop, Colors.blue)),
              ],
            ),
            const SizedBox(height: 24),
            
            // UI original restaurada completa
            const Text('Estabilidad del Sistema', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Color(0xFF004D40))),
            const SizedBox(height: 16),
            Container(
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(16),
              ),
              child: const Column(
                children: [
                  Icon(Icons.eco, size: 60, color: Colors.green),
                  SizedBox(height: 16),
                  Text('Salud Óptima', style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold, color: Colors.green)),
                  Text('Tu cultivo de Lechugas se ha mantenido dentro de los umbrales el 92% del tiempo esta semana.', textAlign: TextAlign.center, style: TextStyle(color: Colors.grey)),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildStatCard(String title, String value, IconData icon, Color color) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.05), blurRadius: 10)],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: color, size: 28),
          const SizedBox(height: 12),
          Text(title, style: const TextStyle(color: Colors.grey, fontSize: 13)),
          const SizedBox(height: 4),
          Text(value, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 20)),
        ],
      ),
    );
  }
}