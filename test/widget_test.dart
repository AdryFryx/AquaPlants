import 'package:flutter_test/flutter_test.dart';
import 'package:aquaplants/main.dart'; 

void main() {
  testWidgets('Verificar carga de LoginScreen', (WidgetTester tester) async {
    // Construye la aplicación de AquaPlants
    await tester.pumpWidget(const AquaPlantsApp());

    // Verifica que el botón de Iniciar Sesión exista en la pantalla
    expect(find.text('Iniciar Sesión'), findsOneWidget);
  });
}