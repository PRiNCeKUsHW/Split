import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flatsplit_mobile/theme/colors.dart';
import 'package:flatsplit_mobile/theme/neobrutalism.dart';

void main() {
  testWidgets('NeobrutalCard renders with child and styling', (WidgetTester tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: NeobrutalCard(
            backgroundColor: AppColors.creditFill,
            child: Text('TEST CARD'),
          ),
        ),
      ),
    );

    expect(find.text('TEST CARD'), findsOneWidget);
  });

  testWidgets('NeobrutalButton renders and responds to tap', (WidgetTester tester) async {
    bool tapped = false;
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: NeobrutalButton(
            text: 'CLICK ME',
            onPressed: () {
              tapped = true;
            },
          ),
        ),
      ),
    );

    expect(find.text('CLICK ME'), findsOneWidget);
    await tester.tap(find.text('CLICK ME'));
    await tester.pumpAndSettle();
    expect(tapped, isTrue);
  });

  testWidgets('MoneyText renders rupee sign with monospace font', (WidgetTester tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: MoneyText(amount: '500.00'),
        ),
      ),
    );

    expect(find.text('₹500.00'), findsOneWidget);
  });
}
