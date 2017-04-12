with
[LinkTravelTime] as
(
    select
        [JourneyLinkRef] = p.[JourneyPointRef],
        j.[JourneyRef],
        
        --jp.JourneyPatternDisplayName,
        p.[SequenceNumber],        
        [DateTime] = isnull([ObservedDepartureDateTime], [PlannedDepartureDateTime]),
        [LineDirectionLinkOrder] = dense_rank() over (partition by jp.[LineDirectionCode] order by sec.[LineDirectionLegacyOrder]),

        jp.[LineDirectionCode],        
        [PeekClass] = case when j.OperatingDayType = 1 and datepart(hour, p.[PlannedDepartureDateTime]) between 7 and 9 then 'PEEK' else 'OFFPEEK' end,
        [LinkRef] = concat(sec.StopPointSectionFromOwner, ':', sec.StopPointSectionFromNumber, '->', sec.StopPointSectionToOwner, ':',sec.StopPointSectionToNumber),
        [LinkName] = sec.StopPointSectionDisplayName,
        [LinkTravelTime] = datediff(second, lag(p.[ObservedDepartureDateTime]) over (partition by j.[JourneyRef] order by p.[JourneyPointRef]), p.[ObservedArrivalDateTime])
    FROM
        [data].[RT_Journey] j
        join [dim].[JourneyPattern] jp on jp.[JourneyPatternId] =  j.[JourneyPatternId] and jp.[IsCurrent] = 1
        join [data].[RT_JourneyPoint] p on p.[JourneyRef] = j.[JourneyRef]
        join [dim].[JourneyPatternSection] sec on sec.JourneyPatternId = jp.[JourneyPatternId] and sec.SequenceNumber = p.SequenceNumber and sec.IsCurrent = 1
    where
        j.[LineDesignation] = '4A'
        and j.[OperatingDayDate] between '2017-01-01' and '2017-01-31'
        and datepart(hour, [PlannedStartDateTime]) in (8, 12)
        and p.[IsStopPoint] = 1
)
select
    [JourneyLinkRef],
    [JourneyRef],    
    [DateTime],
    [LineDirectionLinkOrder],

    [LineDirectionCode],
    [PeekClass],
    [LinkRef],
    [LinkName],
    [LinkTravelTime]
from
    [LinkTravelTime]
where
    [SequenceNumber] > 1
order by
    [JourneyLinkRef]