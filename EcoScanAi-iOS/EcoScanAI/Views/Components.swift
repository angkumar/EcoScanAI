import SwiftUI

struct AnimatedBackgroundView: View {
    @State private var phase: CGFloat = 0

    var body: some View {
        ZStack {
            EcoTheme.backgroundGradient
            Circle()
                .fill(EcoTheme.accent.opacity(0.25))
                .frame(width: 320, height: 320)
                .blur(radius: 70)
                .offset(x: -120 + phase * 16, y: -280)
            Circle()
                .fill(Color.cyan.opacity(0.18))
                .frame(width: 260, height: 260)
                .blur(radius: 70)
                .offset(x: 140 - phase * 10, y: -120)
        }
        .onAppear {
            withAnimation(.easeInOut(duration: 3.0).repeatForever(autoreverses: true)) {
                phase = 1
            }
        }
    }
}

struct ImpactBadgeView: View {
    let score: ImpactScore

    var body: some View {
        HStack(spacing: 8) {
            Circle()
                .fill(score.color)
                .frame(width: 12, height: 12)
            Text("\(score.rawValue) • \(score.label)")
                .font(.system(.subheadline, design: .rounded, weight: .heavy))
                .foregroundStyle(.white)
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 8)
        .background(score.color.opacity(0.25), in: Capsule())
        .overlay(Capsule().stroke(score.color.opacity(0.75), lineWidth: 1))
        .shadow(color: score.color.opacity(0.45), radius: 10, x: 0, y: 5)
    }
}

struct DisposalCardView: View {
    let instruction: DisposalInstruction

    var body: some View {
        HStack(alignment: .top, spacing: 10) {
            Image(systemName: instruction.disposalType.icon)
                .foregroundStyle(EcoTheme.accent)
                .font(.system(size: 22, weight: .bold))

            VStack(alignment: .leading, spacing: 3) {
                Text(instruction.disposalType.rawValue)
                    .font(.system(.headline, design: .rounded, weight: .bold))
                    .foregroundStyle(.white)
                Text(instruction.detail)
                    .font(.system(.footnote, design: .rounded))
                    .foregroundStyle(.white.opacity(0.75))
            }
            Spacer()
        }
        .padding(12)
        .background(Color.white.opacity(0.06), in: RoundedRectangle(cornerRadius: 14))
    }
}
