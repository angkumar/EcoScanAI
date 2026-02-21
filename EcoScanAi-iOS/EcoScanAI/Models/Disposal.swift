import Foundation

enum City: String, CaseIterable, Identifiable, Codable {
    case sanFrancisco = "San Francisco"
    case chicago = "Chicago"

    var id: String { rawValue }
}

enum DisposalType: String, Codable {
    case recycle = "Recycle"
    case trash = "Trash"
    case compost = "Compost"
    case specialDropOff = "Special Drop-off"

    var icon: String {
        switch self {
        case .recycle:
            return "arrow.3.trianglepath"
        case .trash:
            return "trash"
        case .compost:
            return "leaf"
        case .specialDropOff:
            return "shippingbox"
        }
    }
}

struct DisposalInstruction: Codable {
    let city: City
    let disposalType: DisposalType
    let detail: String
}
