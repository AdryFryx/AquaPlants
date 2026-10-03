import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

class ApiService {
  // Cuando levantes Django, cambiaremos esto por la IP de tu PC o servidor AWS
  static const String baseUrl = 'http://127.0.0.1:8000/api'; 

  // Función REAL para iniciar sesión
  Future<bool> login(String email, String password) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/token/'), // Endpoint típico de Django JWT
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'username': email,
          'password': password,
        }),
      );

      if (response.statusCode == 200) {
        // Si Django responde OK, extraemos el Token
        final data = jsonDecode(response.body);
        final token = data['access']; // Depende de cómo configures Django (ej. SimpleJWT)

        // Guardamos el token encriptado en el almacenamiento del celular
        final prefs = await SharedPreferences.getInstance();
        await prefs.setString('jwt_token', token);
        
        return true; // Login exitoso
      } else {
        return false; // Credenciales incorrectas
      }
    } catch (e) {
      print('Error de conexión: $e');
      return false; // Error de red o servidor caído
    }
  }

  Future<List<dynamic>> getMediciones() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final token = prefs.getString('jwt_token'); // Rescatamos el token guardado

      if (token == null) return []; // Si no hay token, no hacemos la petición

      final response = await http.get(
        Uri.parse('$baseUrl/mediciones/'),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $token', // Mandamos la llave mágica de JWT
        },
      );

      if (response.statusCode == 200) {
        // Si sale bien, devolvemos la lista de datos
        return jsonDecode(response.body); 
      } else {
        print('Error del servidor: ${response.statusCode}');
        return [];
      }
    } catch (e) {
      print('Error de red: $e');
      return [];
    }
  }

  // Función para cerrar sesión (borrar el token)
  Future<void> logout() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('jwt_token');
  }
}