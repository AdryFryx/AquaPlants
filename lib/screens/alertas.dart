import 'package:flutter/material.dart';
import '../services/api_service.dart';

class AlertasScreen extends StatefulWidget {
  const AlertasScreen({super.key});

  @override
  State<AlertasScreen> createState() => _AlertasScreenState();
}

class _AlertasScreenState extends State<AlertasScreen> {
  final ApiService _apiService = ApiService();
  List<dynamic> _alertas = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _cargarAlertas();
  }

  Future<void> _cargarAlertas() async {
    final datos = await _apiService.getAlertas();
    if (mounted) {
      setState(() {
        _alertas = datos;
        _isLoading = false;
      });
    }
  }

  Future<void> _marcarComoLeida(int id, int index) async {
    setState(() {
      _alertas.removeAt(index);
    });
    await _apiService.resolverAlerta(id);
  }

  void _mostrarModalReporteFalla() {
    String motivoSeleccionado = 'Bomba no funciona';
    final TextEditingController detalleController = TextEditingController();
    bool enviando = false;

    showModalBottomSheet(
      context: context,
      isScrollControlled: true, // Evita que el teclado tape el campo de texto
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (modalContext) {
        return StatefulBuilder(
          builder: (context, setModalState) {
            return Padding(
              padding: EdgeInsets.only(
                left: 20,
                right: 20,
                top: 20,
                bottom: MediaQuery.of(context).viewInsets.bottom + 20,
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Reportar Falla del Dispositivo',
                    style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Color(0xFFD32F2F)),
                  ),
                  const SizedBox(height: 8),
                  const Text(
                    'Selecciona el problema que estás presentando:',
                    style: TextStyle(color: Colors.grey),
                  ),
                  const SizedBox(height: 12),

                  RadioListTile<String>(
                    title: const Text('Bomba no funciona'),
                    value: 'Bomba no funciona',
                    groupValue: motivoSeleccionado,
                    activeColor: const Color(0xFFD32F2F),
                    onChanged: (val) => setModalState(() => motivoSeleccionado = val!),
                  ),
                  RadioListTile<String>(
                    title: const Text('Sin Conexión'),
                    value: 'Sin Conexión',
                    groupValue: motivoSeleccionado,
                    activeColor: const Color(0xFFD32F2F),
                    onChanged: (val) => setModalState(() => motivoSeleccionado = val!),
                  ),
                  RadioListTile<String>(
                    title: const Text('Otro'),
                    value: 'Otro',
                    groupValue: motivoSeleccionado,
                    activeColor: const Color(0xFFD32F2F),
                    onChanged: (val) => setModalState(() => motivoSeleccionado = val!),
                  ),

                  // Cuadro de texto condicional solo si elige "Otro"
                  if (motivoSeleccionado == 'Otro') ...[
                    const SizedBox(height: 8),
                    TextField(
                      controller: detalleController,
                      maxLines: 3,
                      decoration: InputDecoration(
                        labelText: 'Describe qué está fallando o pasando',
                        border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                      ),
                    ),
                  ],

                  const SizedBox(height: 20),
                  SizedBox(
                    width: double.infinity,
                    height: 48,
                    child: ElevatedButton(
                      style: ElevatedButton.styleFrom(
                        backgroundColor: const Color(0xFFD32F2F),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                      ),
                      onPressed: enviando
                          ? null
                          : () async {
                              if (motivoSeleccionado == 'Otro' && detalleController.text.trim().isEmpty) {
                                ScaffoldMessenger.of(this.context).showSnackBar(
                                  const SnackBar(content: Text('Por favor describe el problema.')),
                                );
                                return;
                              }

                              setModalState(() => enviando = true);
                              final exito = await _apiService.reportarFalla(
                                motivoSeleccionado,
                                detalleController.text.trim(),
                              );

                              if (!mounted) return;
                              Navigator.pop(modalContext);

                              ScaffoldMessenger.of(this.context).showSnackBar(
                                SnackBar(
                                  content: Text(
                                    exito
                                        ? 'Reporte enviado al administrador.'
                                        : 'No se pudo enviar el reporte. Intenta nuevamente.',
                                  ),
                                  backgroundColor: exito ? Colors.green : Colors.red,
                                ),
                              );
                            },
                      child: enviando
                          ? const SizedBox(
                              height: 22,
                              width: 22,
                              child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2),
                            )
                          : const Text(
                              'Enviar Reporte',
                              style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 16),
                            ),
                    ),
                  ),
                ],
              ),
            );
          },
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.grey[100],
      appBar: AppBar(
        title: const Text('Centro de Alertas', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
        backgroundColor: const Color(0xFFD32F2F),
        elevation: 0,
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _mostrarModalReporteFalla,
        backgroundColor: const Color(0xFFD32F2F),
        icon: const Icon(Icons.build_circle_outlined, color: Colors.white),
        label: const Text('Reportar Falla', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _alertas.isEmpty
              ? const Center(
                  child: Text('Todo tranquilo. No hay alertas.', style: TextStyle(fontSize: 16, color: Colors.grey)),
                )
              : ListView.builder(
                  padding: const EdgeInsets.only(left: 16, right: 16, top: 16, bottom: 80),
                  itemCount: _alertas.length,
                  itemBuilder: (context, index) {
                    final alerta = _alertas[index];
                    return Card(
                      elevation: 2,
                      margin: const EdgeInsets.only(bottom: 12),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                      child: ListTile(
                        contentPadding: const EdgeInsets.all(16),
                        leading: CircleAvatar(
                          backgroundColor: Colors.red[50],
                          child: const Icon(Icons.warning_amber_rounded, color: Colors.red),
                        ),
                        title: Text(alerta['mensaje'], style: const TextStyle(fontWeight: FontWeight.bold)),
                        trailing: IconButton(
                          icon: const Icon(Icons.check_circle_outline, color: Colors.green, size: 30),
                          onPressed: () => _marcarComoLeida(alerta['id'], index),
                        ),
                      ),
                    );
                  },
                ),
    );
  }
}