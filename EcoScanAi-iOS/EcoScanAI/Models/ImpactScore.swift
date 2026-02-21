import SwiftUI

enum ImpactScore: String, Codable, CaseIterable {
    case green = "Green"
    case yellow = "Yellow"
    case red = "Red"

    var label: String {
        switch self {
        case .green:
            return "Low Impact"
        case .yellow:
            return "Medium Impact"
        case .red:
            return "High Impact"
        }
    }

    var co2Estimate: Double {
        switch self {
        case .red:
            return 5.0
        case .yellow:
            return 2.5
        case .green:
            return 0.8
        }
    }

    var color: Color {
        switch self {
        case .green:
            return Color(red: 0.24, green: 1.0, blue: 0.71)
        case .yellow:
            return Color(red: 1.0, green: 0.88, blue: 0.40)
        case .red:
            return Color(red: 1.0, green: 0.38, blue: 0.46)
        }
    }
}
