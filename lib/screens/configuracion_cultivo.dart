
import 'package:flutter/material.dart';
import '../services/api_service.dart';

class ConfiguracionCultivoScreen extends StatefulWidget {
  const ConfiguracionCultivoScreen({super.key});

  @override
  State<ConfiguracionCultivoScreen> createState() =>
      _ConfiguracionCultivoScreenState();
}

class _ConfiguracionCultivoScreenState
    extends State<ConfiguracionCultivoScreen> {
  final _formKey = GlobalKey<FormState>();

  final _plantaController = TextEditingController();
  final _tempMinController = TextEditingController();
  final _tempMaxController = TextEditingController();
  final _phMinController = TextEditingController();
  final _phMaxController = TextEditingController();
  final _aguaMinController = TextEditingController();
  final _aguaMaxController = TextEditingController();

  bool _isLoading = true;
  bool _isSaving = false;
  bool _errorCarga = false;

  @override
  void initState() {
    super.initState();
    _cargarConfiguracion();
  }

  @override
  void dispose() {
    _plantaController.dispose();
    _tempMinController.dispose();
    _tempMaxController.dispose();
    _phMinController.dispose();
    _phMaxController.dispose();
    _aguaMinController.dispose();
    _aguaMaxController.dispose();
    super.dispose();
  }

  Future<void> _cargarConfiguracion() async {
    setState(() {
      _isLoading = true;
      _errorCarga = false;
    });

    final data = await ApiService().obtenerConfiguracion();

    if (!mounted) return;

    if (data == null) {
      setState(() {
        _isLoading = false;
        _errorCarga = true;
      });
      return;
    }

    final reglas = data['reglas'] as Map<String, dynamic>? ?? {};

    void cargarRango(
      String variable,
      TextEditingController minimo,
      TextEditingController maximo,
    ) {
      final regla = reglas[variable] as Map<String, dynamic>?;

      if (regla != null) {
        minimo.text = regla['minimo']?.toString() ?? '';
        maximo.text = regla['maximo']?.toString() ?? '';
      }
    }

    setState(() {
      _plantaController.text = data['tipo_planta']?.toString() ?? '';

      cargarRango('TEMP', _tempMinController, _tempMaxController);
      cargarRango('PH', _phMinController, _phMaxController);
      cargarRango('AGUA', _aguaMinController, _aguaMaxController);

      _isLoading = false;
    });
  }

  String? _validarNumero(String? value) {
    if (value == null || value.trim().isEmpty) {
      return 'Campo obligatorio';
    }

    final numero = double.tryParse(value.trim());

    if (numero == null || !numero.isFinite) {
      return 'Ingresa un número válido';
    }

    return null;
  }

  bool _validarRango(
    TextEditingController minimo,
    TextEditingController maximo,
  ) {
    final min = double.tryParse(minimo.text);
    final max = double.tryParse(maximo.text);

    return min != null && max != null && min < max;
  }

  Future<void> _guardarConfiguracion() async {
    if (!_formKey.currentState!.validate()) return;

    if (!_validarRango(_tempMinController, _tempMaxController) ||
        !_validarRango(_phMinController, _phMaxController) ||
        !_validarRango(_aguaMinController, _aguaMaxController)) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text(
            'Cada valor mínimo debe ser menor que el máximo.',
          ),
          backgroundColor: Colors.red,
        ),
      );
      return;
    }

    setState(() => _isSaving = true);

    final exito = await ApiService().guardarConfiguracion(
      _plantaController.text.trim(),
      _tempMinController.text.trim(),
      _tempMaxController.text.trim(),
      _phMinController.text.trim(),
      _phMaxController.text.trim(),
      _aguaMinController.text.trim(),
      _aguaMaxController.text.trim(),
    );

    if (!mounted) return;

    setState(() => _isSaving = false);

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          exito
              ? 'Configuración guardada correctamente.'
              : 'No se pudo guardar la configuración.',
        ),
        backgroundColor: exito ? Colors.green : Colors.red,
      ),
    );

    if (exito) {
      Navigator.pop(context);
    }
  }

  Widget _campo(
    String etiqueta,
    TextEditingController controller,
    IconData icono,
  ) {
    return Expanded(
      child: TextFormField(
        controller: controller,
        keyboardType: const TextInputType.numberWithOptions(decimal: true),
        validator: _validarNumero,
        decoration: InputDecoration(
          labelText: etiqueta,
          prefixIcon: Icon(icono),
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(12),
          ),
        ),
      ),
    );
  }

  Widget _seccion(String titulo, IconData icono) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 14, top: 24),
      child: Row(
        children: [
          Icon(icono, color: const Color(0xFF008F7A)),
          const SizedBox(width: 8),
          Text(
            titulo,
            style: const TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.bold,
              color: Color(0xFF004D40),
            ),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.grey[100],
      appBar: AppBar(
        title: const Text(
          'Configurar Cultivo',
          style: TextStyle(
            color: Colors.white,
            fontWeight: FontWeight.bold,
          ),
        ),
        backgroundColor: const Color(0xFF00BFA5),
        iconTheme: const IconThemeData(color: Colors.white),
        elevation: 0,
      ),
      body: _isLoading
          ? const Center(
              child: CircularProgressIndicator(
                color: Color(0xFF00BFA5),
              ),
            )
          : _errorCarga
              ? Center(
                  child: Padding(
                    padding: const EdgeInsets.all(24),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const Icon(
                          Icons.cloud_off,
                          size: 48,
                          color: Colors.red,
                        ),
                        const SizedBox(height: 12),
                        const Text(
                          'No se pudo cargar la configuración.',
                          textAlign: TextAlign.center,
                        ),
                        const SizedBox(height: 16),
                        ElevatedButton(
                          onPressed: _cargarConfiguracion,
                          child: const Text('Reintentar'),
                        ),
                      ],
                    ),
                  ),
                )
              : SingleChildScrollView(
                  padding: const EdgeInsets.all(24),
                  child: Form(
                    key: _formKey,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        _seccion('Datos del Cultivo', Icons.grass),
                        TextFormField(
                          controller: _plantaController,
                          validator: (value) =>
                              value == null || value.trim().isEmpty
                                  ? 'Ingresa el tipo de planta'
                                  : null,
                          decoration: InputDecoration(
                            labelText: 'Tipo de Planta',
                            prefixIcon: const Icon(Icons.eco),
                            border: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(12),
                            ),
                          ),
                        ),
                        _seccion('Temperatura (°C)', Icons.thermostat),
                        Row(
                          children: [
                            _campo(
                              'Mínima',
                              _tempMinController,
                              Icons.arrow_downward,
                            ),
                            const SizedBox(width: 12),
                            _campo(
                              'Máxima',
                              _tempMaxController,
                              Icons.arrow_upward,
                            ),
                          ],
                        ),
                        _seccion('Nivel de pH', Icons.science),
                        Row(
                          children: [
                            _campo(
                              'Mínimo',
                              _phMinController,
                              Icons.arrow_downward,
                            ),
                            const SizedBox(width: 12),
                            _campo(
                              'Máximo',
                              _phMaxController,
                              Icons.arrow_upward,
                            ),
                          ],
                        ),
                        _seccion('Nivel de Agua', Icons.water_drop),
                        Row(
                          children: [
                            _campo(
                              'Mínimo',
                              _aguaMinController,
                              Icons.arrow_downward,
                            ),
                            const SizedBox(width: 12),
                            _campo(
                              'Máximo',
                              _aguaMaxController,
                              Icons.arrow_upward,
                            ),
                          ],
                        ),
                        const SizedBox(height: 36),
                        SizedBox(
                          width: double.infinity,
                          height: 52,
                          child: ElevatedButton(
                            style: ElevatedButton.styleFrom(
                              backgroundColor: const Color(0xFF00BFA5),
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(12),
                              ),
                            ),
                            onPressed:
                                _isSaving ? null : _guardarConfiguracion,
                            child: _isSaving
                                ? const CircularProgressIndicator(
                                    color: Colors.white,
                                  )
                                : const Text(
                                    'Guardar Cambios',
                                    style: TextStyle(
                                      fontSize: 17,
                                      color: Colors.white,
                                      fontWeight: FontWeight.bold,
                                    ),
                                  ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
    );
  }
}
