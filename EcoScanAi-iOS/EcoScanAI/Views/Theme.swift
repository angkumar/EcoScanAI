import SwiftUI

enum EcoTheme {
    static let background = Color(red: 0.055, green: 0.067, blue: 0.090)
    static let accent = Color(red: 0.0, green: 1.0, blue: 0.50)
    static let card = Color.white.opacity(0.08)
    static let stroke = Color.white.opacity(0.18)

    static var backgroundGradient: LinearGradient {
        LinearGradient(
            colors: [
                Color(red: 0.03, green: 0.05, blue: 0.07),
                background,
                Color(red: 0.02, green: 0.06, blue: 0.10)
            ],
            startPoint: .topLeading,
            endPoint: .bottomTrailing
        )
    }
}

struct GlowCardModifier: ViewModifier {
    func body(content: Content) -> some View {
        content
            .padding(16)
            .background(EcoTheme.card)
            .overlay(RoundedRectangle(cornerRadius: 22).stroke(EcoTheme.stroke, lineWidth: 1))
            .clipShape(RoundedRectangle(cornerRadius: 22))
            .shadow(color: EcoTheme.accent.opacity(0.25), radius: 14, x: 0, y: 6)
    }
}

extension View {
    func glowCard() -> some View {
        modifier(GlowCardModifier())
    }
}
