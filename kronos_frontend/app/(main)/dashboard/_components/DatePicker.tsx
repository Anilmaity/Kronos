// React - Next default
import React from "react";

// Icons
import { CalendarIcon } from "lucide-react";

// Utils
import { cn } from "@/lib/utils";
import { dateFormatter } from "@/utils/dateFormatter";

// Components
import { Button } from "@/components/ui/button";
import { Calendar } from "@/components/ui/calendar";

import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";

interface DatePickerProps {
  selectedDate: Date;
  onSelectDate: (date: Date) => void;
  createdAtDate: Date;
}

// DatePicker Component
const DatePicker: React.FC<DatePickerProps> = ({
  selectedDate,
  onSelectDate,
  createdAtDate,
}) => {
  const [date, setDate] = React.useState<Date>(selectedDate);

  function isWeekend(date: Date) {
    const day = date.getDay();
    return day === 0 || day === 6;
  } // Check if the date is a weekend

  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button
          variant={"outline"}
          className={cn(
            "w-[280px] justify-start text-left font-normal",
            !date && "text-muted-foreground"
          )}
        >
          <CalendarIcon className="mr-2 h-4 w-4" />
          {date ? (
            dateFormatter(selectedDate.toISOString().split("T")[0])
          ) : (
            <span>Pick a date</span>
          )}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-auto p-0">
        <Calendar
          mode="single"
          selected={date}
          onSelect={(newDate) => {
            if (newDate) {
              setDate(newDate);
              onSelectDate(newDate);
            }
          }}
          disabled={(newDate) => {
            const isDisabled =
              newDate > new Date() ||
              newDate < new Date(createdAtDate.setHours(0, 0, 0, 0)) ;

            return isDisabled;
          }}
          initialFocus
        />
      </PopoverContent>
    </Popover>
  );
};

export default DatePicker;
