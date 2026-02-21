import Foundation

struct ScanRecord: Identifiable, Codable {
    let id: UUID
    let barcode: String
    let productName: String
    let category: String
    let city: City
    let impactScore: ImpactScore
    let co2Estimate: Double
    let disposalType: DisposalType
    let timestamp: Date
}
