import Foundation
import CoreData
import Combine

final class ScanStore {
    private let container: NSPersistentContainer
    private let subject = CurrentValueSubject<[ScanRecord], Never>([])

    var scansPublisher: AnyPublisher<[ScanRecord], Never> {
        subject.eraseToAnyPublisher()
    }

    init() {
        let model = Self.makeModel()
        container = NSPersistentContainer(name: "EcoScanAI", managedObjectModel: model)

        if let description = container.persistentStoreDescriptions.first {
            let storeURL = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)
                .first?
                .appendingPathComponent("EcoScanAI.sqlite")
            description.url = storeURL
            description.shouldMigrateStoreAutomatically = true
            description.shouldInferMappingModelAutomatically = true
        }

        container.loadPersistentStores { _, error in
            if let error {
                assertionFailure("Persistent store load failed: \(error.localizedDescription)")
            }
        }

        fetchAll()
    }

    func save(record: ScanRecord) {
        let context = container.viewContext
        let object = NSEntityDescription.insertNewObject(forEntityName: "ScanEntity", into: context)
        object.setValue(record.id, forKey: "id")
        object.setValue(record.barcode, forKey: "barcode")
        object.setValue(record.productName, forKey: "productName")
        object.setValue(record.category, forKey: "category")
        object.setValue(record.city.rawValue, forKey: "city")
        object.setValue(record.impactScore.rawValue, forKey: "impactScore")
        object.setValue(record.co2Estimate, forKey: "co2Estimate")
        object.setValue(record.disposalType.rawValue, forKey: "disposalType")
        object.setValue(record.timestamp, forKey: "timestamp")

        do {
            try context.save()
            fetchAll()
        } catch {
            context.rollback()
        }
    }

    func fetchAll() {
        let request = NSFetchRequest<NSManagedObject>(entityName: "ScanEntity")
        request.sortDescriptors = [NSSortDescriptor(key: "timestamp", ascending: false)]

        do {
            let objects = try container.viewContext.fetch(request)
            let scans = objects.compactMap(Self.map)
            subject.send(scans)
        } catch {
            subject.send([])
        }
    }

    func monthlyReport(month: Date) -> [ScanRecord] {
        let calendar = Calendar.current
        guard let start = calendar.date(from: calendar.dateComponents([.year, .month], from: month)),
              let end = calendar.date(byAdding: .month, value: 1, to: start) else {
            return []
        }

        return subject.value.filter { $0.timestamp >= start && $0.timestamp < end }
    }

    private static func map(_ object: NSManagedObject) -> ScanRecord? {
        guard
            let id = object.value(forKey: "id") as? UUID,
            let barcode = object.value(forKey: "barcode") as? String,
            let productName = object.value(forKey: "productName") as? String,
            let category = object.value(forKey: "category") as? String,
            let cityRaw = object.value(forKey: "city") as? String,
            let city = City(rawValue: cityRaw),
            let impactRaw = object.value(forKey: "impactScore") as? String,
            let impactScore = ImpactScore(rawValue: impactRaw),
            let disposalRaw = object.value(forKey: "disposalType") as? String,
            let disposalType = DisposalType(rawValue: disposalRaw),
            let timestamp = object.value(forKey: "timestamp") as? Date
        else {
            return nil
        }

        let co2Estimate = object.value(forKey: "co2Estimate") as? Double ?? impactScore.co2Estimate

        return ScanRecord(
            id: id,
            barcode: barcode,
            productName: productName,
            category: category,
            city: city,
            impactScore: impactScore,
            co2Estimate: co2Estimate,
            disposalType: disposalType,
            timestamp: timestamp
        )
    }

    private static func makeModel() -> NSManagedObjectModel {
        let model = NSManagedObjectModel()
        let entity = NSEntityDescription()
        entity.name = "ScanEntity"
        entity.managedObjectClassName = NSStringFromClass(NSManagedObject.self)

        func attribute(_ name: String, _ type: NSAttributeType, optional: Bool = false) -> NSAttributeDescription {
            let attribute = NSAttributeDescription()
            attribute.name = name
            attribute.attributeType = type
            attribute.isOptional = optional
            return attribute
        }

        entity.properties = [
            attribute("id", .UUIDAttributeType),
            attribute("barcode", .stringAttributeType),
            attribute("productName", .stringAttributeType),
            attribute("category", .stringAttributeType),
            attribute("city", .stringAttributeType),
            attribute("impactScore", .stringAttributeType),
            attribute("co2Estimate", .doubleAttributeType),
            attribute("disposalType", .stringAttributeType),
            attribute("timestamp", .dateAttributeType)
        ]

        model.entities = [entity]
        return model
    }
}
